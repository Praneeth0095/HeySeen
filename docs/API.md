# HeySeen API Documentation

## Overview
HeySeen provides a RESTful API for converting PDF documents into LaTeX and images. The service runs asynchronously, using a job queue system.

**Base URL**: `http://localhost:5555` (or your tunnel URL)

---

## Endpoints

### 1. Health Check
Check if the service is running.

- **URL**: `/health`
- **Method**: `GET`
- **Response**:
  ```json
  {
    "status": "ok",
    "version": "0.1.0"
  }
  ```

---

### 2. Create Conversion Job
Upload a PDF for processing.

- **URL**: `/convert`
- **Method**: `POST`
- **Parameters**:
  - `file`: (File, Required) The PDF file to upload.
  - `math_ocr`: (Boolean, Optional) Enable Math OCR. Default: `true`.
  - `dpi`: (Integer, Optional) Resolution for rasterizing pages. Default: `150`.
- **Response**:
  ```json
  {
    "job_id": "565da703-d586-480c-a123-5fcf86947fd3",
    "status": "queued",
    "message": "Queued",
    "progress": 0.0,
    "created_at": 1707123456.78
  }
  ```

---

### 3. Get Job Status
Poll the status of a conversion job.

- **URL**: `/status/{job_id}`
- **Method**: `GET`
- **Path Parameters**:
  - `job_id`: The ID returned from the conversion request.
- **Response**:
  ```json
  {
    "job_id": "565da703-d586-480c-a123-5fcf86947fd3",
    "status": "processing",
    "message": "Extracting Content (OCR in progress)...",
    "progress": 0.45,
    "created_at": 1707123456.78
  }
  ```
- **Statuses**: `queued`, `processing`, `completed`, `failed`.

---

### 4. Download Result
Download the converted output (ZIP file containing TeX and images).

- **URL**: `/download/{job_id}`
- **Method**: `GET`
- **Path Parameters**:
  - `job_id`: The ID of a **completed** job.
- **Response**: Binary file stream (`application/zip`).

---

## Example Usage (Python)

```python
import requests
import time

API_URL = "http://localhost:5555"

# 1. Upload
files = {'file': open('paper.pdf', 'rb')}
r = requests.post(f"{API_URL}/convert", files=files, params={"math_ocr": True})
data = r.json()
job_id = data['job_id']
print(f"Job submitted: {job_id}")

# 2. Poll
while True:
    status = requests.get(f"{API_URL}/status/{job_id}").json()
    print(f"Progress: {status['progress']*100:.1f}% - {status['message']}")
    
    if status['status'] == 'completed':
        break
    if status['status'] == 'failed':
        print("Error!")
        exit(1)
    time.sleep(1)

# 3. Download
with open("result.zip", "wb") as f:
    resp = requests.get(f"{API_URL}/download/{job_id}")
    f.write(resp.content)
print("Saved to result.zip")
```
