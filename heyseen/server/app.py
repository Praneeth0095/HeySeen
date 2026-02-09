import shutil
import uuid
import logging
import threading
import zipfile
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
from enum import Enum

from fastapi import FastAPI, UploadFile, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from heyseen.core.pdf_loader import load_pdf
from heyseen.core.layout_analyzer import LayoutAnalyzer
from heyseen.core.content_extractor import ContentExtractor
from heyseen.core.tex_builder import TeXBuilder
from heyseen.core.model_manager import ModelManager
from heyseen.server.user_manager import UserManager

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "server_data/uploads"
OUTPUT_DIR = BASE_DIR / "server_data/outputs"
USER_DATA_DIR = BASE_DIR / "server_data/users"
STATIC_DIR = Path(__file__).resolve().parent / "static"

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# User Manager
user_manager = UserManager(USER_DATA_DIR)

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HeySeenAPI")

app = FastAPI(title="HeySeen API", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global State
jobs: Dict[str, Dict[str, Any]] = {}

class JobStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    message: Optional[str] = None
    progress: float = 0.0
    created_at: float

# User Models
class SignUpRequest(BaseModel):
    email: str
    name: str
    password_hash: str

class LoginRequest(BaseModel):
    email: str
    password_hash: str

class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    avatar: Optional[str] = None
    lastLogin: Optional[int] = None
    projectCount: Optional[int] = None

class UpdateRoleRequest(BaseModel):
    new_role: str
    admin_email: str

def process_pdf_job(job_id: str, file_path: Path, use_math_ocr: bool, dpi: int, use_llm: bool = False):
    """Background task to process PDF."""
    try:
        logger.info(f"Job {job_id}: Started processing {file_path.name}")
        jobs[job_id]["status"] = JobStatus.PROCESSING
        jobs[job_id]["progress"] = 0.1
        
        job_output_dir = OUTPUT_DIR / job_id
        job_output_dir.mkdir(parents=True, exist_ok=True)
        
        # 0. Load Models (Lazy, Singleton)
        manager = ModelManager.get_instance("mps") # Default to MPS on Mac
        
        # 1. Load PDF
        start_time = time.time()
        jobs[job_id]["message"] = "Loading PDF..."
        pages = load_pdf(file_path, dpi=dpi)
        jobs[job_id]["progress"] = 0.2
        
        # 2. Layout Analysis
        jobs[job_id]["message"] = "Analyzing Layout..."
        analyzer = LayoutAnalyzer(device="mps", verbose=False, manager=manager)
        all_blocks = []
        for i, page in enumerate(pages):
            blocks = analyzer.detect_layout(page.image)
            blocks = analyzer.sort_reading_order(blocks)
            all_blocks.append(blocks)
            # Update progress linearly for layout (20% to 50%)
            jobs[job_id]["progress"] = 0.2 + (0.3 * (i + 1) / len(pages))
            
        # 3. Content Extraction
        jobs[job_id]["message"] = "Extracting Content (OCR in progress)..."
        extractor = ContentExtractor(device="mps", use_math_ocr=use_math_ocr, verbose=False, manager=manager)
        all_contents = []
        images_dir = job_output_dir / "images"
        
        for i, (page, blocks) in enumerate(zip(pages, all_blocks)):
            contents = extractor.extract_page(page.image, blocks, output_dir=images_dir)
            all_contents.append(contents)
            # Update progress linearly for extraction (50% to 90%)
            jobs[job_id]["progress"] = 0.5 + (0.4 * (i + 1) / len(pages))
            
        # 4. Build LaTeX
        jobs[job_id]["message"] = "Building LaTeX Document..."
        builder = TeXBuilder(output_dir=job_output_dir, verbose=False)
        document_info = {
            "title": file_path.stem.replace("_", " ").title(),
            "author": "HeySeen Web"
        }
        main_tex_path = builder.build_document(all_contents, all_blocks, document_info)
        
        # 4.5. Optional LLM Post-processing
        if use_llm:
            jobs[job_id]["message"] = "Applying LLM corrections..."
            jobs[job_id]["progress"] = 0.92
            try:
                from heyseen.core.latex_corrector import LatexCorrector
                corrector = LatexCorrector(llm_url="http://localhost:11434", model="qwen2.5-coder:7b")
                corrector.correct_file(str(main_tex_path), str(main_tex_path.with_stem(main_tex_path.stem + "_corrected")))
                logger.info(f"Job {job_id}: LLM correction applied")
            except Exception as e:
                logger.warning(f"Job {job_id}: LLM correction failed: {e}")
        
        # 5. Zip Result
        zip_path = OUTPUT_DIR / f"{job_id}.zip"
        shutil.make_archive(str(zip_path.with_suffix("")), 'zip', job_output_dir)
        
        duration = time.time() - start_time
        jobs[job_id]["status"] = JobStatus.COMPLETED
        jobs[job_id]["progress"] = 1.0
        jobs[job_id]["message"] = f"Completed in {duration:.1f}s"
        jobs[job_id]["result_file"] = str(zip_path)
        logger.info(f"Job {job_id}: Completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        jobs[job_id]["status"] = JobStatus.FAILED
        jobs[job_id]["message"] = str(e)

@app.on_event("startup")
async def startup_event():
    # Pre-load models to ensure speed
    logger.info("Initializing ModelManager on Startup...")
    # Run in thread to not block startup if it takes long? 
    # Actually, let's load on first request or just init structure.
    # ModelManager.get_instance("mps").get_layout_predictor() 
    pass

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "0.1.0"}

# ==================== User Management APIs ====================

@app.post("/api/users/signup")
def signup(request: SignUpRequest):
    """Create a new user"""
    try:
        user = user_manager.create_user(
            email=request.email,
            name=request.name,
            password_hash=request.password_hash
        )
        # Don't return password in response
        user_response = {k: v for k, v in user.items() if k != "password"}
        return {"success": True, "user": user_response}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except Exception as e:
        logger.error(f"Signup error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")

@app.post("/api/users/login")
def login(request: LoginRequest):
    """Login user"""
    try:
        # Verify password
        if not user_manager.verify_password(request.email, request.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Get user
        user = user_manager.get_user(request.email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update last login
        user_manager.update_user(request.email, {
            "lastLogin": int(datetime.now().timestamp() * 1000)
        })
        
        # Don't return password
        user_response = {k: v for k, v in user.items() if k != "password"}
        return {"success": True, "user": user_response}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/api/users/{email}")
def get_user(email: str):
    """Get user by email"""
    user = user_manager.get_user(email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Don't return password
    user_response = {k: v for k, v in user.items() if k != "password"}
    return {"success": True, "user": user_response}

@app.put("/api/users/{email}")
def update_user(email: str, request: UpdateUserRequest):
    """Update user information"""
    try:
        updates = {k: v for k, v in request.dict().items() if v is not None}
        user = user_manager.update_user(email, updates)
        
        # Don't return password
        user_response = {k: v for k, v in user.items() if k != "password"}
        return {"success": True, "user": user_response}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")

@app.get("/api/users")
def get_all_users(admin_email: str):
    """Get all users (admin only)"""
    try:
        users = user_manager.get_all_users(admin_email)
        # Don't return passwords
        users_response = [{k: v for k, v in user.items() if k != "password"} for user in users]
        return {"success": True, "users": users_response}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Get all users error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get users")

@app.put("/api/users/{email}/role")
def update_user_role(email: str, request: UpdateRoleRequest):
    """Update user role (admin only)"""
    try:
        user = user_manager.update_role(email, request.new_role, request.admin_email)
        
        # Don't return password
        user_response = {k: v for k, v in user.items() if k != "password"}
        return {"success": True, "user": user_response}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Update role error: {e}")
        raise HTTPException(status_code=500, detail="Failed to update role")

@app.delete("/api/users/{email}")
def delete_user(email: str, admin_email: str):
    """Delete user (admin only)"""
    try:
        user_manager.delete_user(email, admin_email)
        return {"success": True, "message": f"User {email} deleted"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")

# ==================== PDF Conversion APIs ====================

@app.post("/convert", response_model=JobResponse)
async def create_conversion_job(
    file: UploadFile, 
    background_tasks: BackgroundTasks,
    math_ocr: bool = True,
    dpi: int = 150,
    use_llm: bool = False
):
    job_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{job_id}_{file.filename}"
    
    # Save uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Initialize job state
    jobs[job_id] = {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "message": "Queued",
        "progress": 0.0,
        "created_at": time.time(),
        "input_file": str(file_path)
    }
    
    # Start background task
    background_tasks.add_task(process_pdf_job, job_id, file_path, math_ocr, dpi, use_llm)
    
    return JobResponse(**jobs[job_id])

@app.get("/status/{job_id}", response_model=JobResponse)
def get_job_status(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobResponse(**jobs[job_id])

@app.get("/download/{job_id}")
def download_result(job_id: str):
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed")
    
    result_file = Path(job.get("result_file", ""))
    if not result_file.exists():
        raise HTTPException(status_code=500, detail="Result file missing")
        
    return FileResponse(
        path=result_file, 
        filename=f"heyseen_output_{job_id}.zip",
        media_type="application/zip"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5555)

# Mount Static Files at root (Must be last to avoid overriding API routes)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
