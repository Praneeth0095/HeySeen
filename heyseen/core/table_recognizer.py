"""
Table Recognizer Module

Uses Microsoft's Table Transformer (TATR) to detect table structure 
and reconstructs LaTeX tables using HeySeen's OCR for cell content.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Callable, Dict
import torch
from PIL import Image
import numpy as np

from .model_manager import ModelManager

@dataclass
class TableCell:
    """A cell in a detected table"""
    bbox: List[float] # [x0, y0, x1, y1] original image coordinates
    row_idx: int = -1
    col_idx: int = -1
    row_span: int = 1
    col_span: int = 1
    content: str = ""
    is_header: bool = False

class TableRecognizer:
    def __init__(self, device: str = "mps", manager: Optional[ModelManager] = None):
        if manager is None:
            manager = ModelManager.get_instance(device)
            
        self.device = device
        self.model, self.processor = manager.get_table_model()
        
        if not self.model:
            print("Warning: Table Transformer model not available.")

    def process_table(self, image: Image.Image, ocr_callback: Callable[[Image.Image], str]) -> str:
        """
        Process a table image Crop -> LaTeX code.
        
        Args:
            image: PIL Image of the table region
            ocr_callback: Function that takes an image crop and returns text content
            
        Returns:
            LaTeX tabular code
        """
        if not self.model:
            print("Warning: Table Transformer model not available.")

    def process_table(self, image: Image.Image, ocr_callback: Callable[[Image.Image], str]) -> str:
        """
        Process a table image Crop -> LaTeX code.
        
        Args:
            image: PIL Image of the table region
            ocr_callback: Function that takes an image crop and returns text content
            
        Returns:
            LaTeX tabular code
        """
        if not self.model:
            return "% Table recognition unavailable\n"
        
        # Debug: Print image size
        # print(f"DEBUG: Processing table image size: {image.size}")

        # 1. Structure Recognition
        cells = self._detect_structure(image)
        if not cells:
            # print("DEBUG: No cells detected")
            return "" # Return empty to trigger fallback? Or return comment?
            
        # 2. OCR Content for each cell
        # Combine cell crops into batches? For now, simple loop
        for cell in cells:
            # Crop cell
            # bbox is [x0, y0, x1, y1]
            crop_box = (
                max(0, int(cell.bbox[0])),
                max(0, int(cell.bbox[1])),
                min(image.width, int(cell.bbox[2])),
                min(image.height, int(cell.bbox[3]))
            )
            
            # Avoid invalid crops
            if crop_box[2] <= crop_box[0] or crop_box[3] <= crop_box[1]:
                continue
            
            # Pad slightly to capture border text? 
            # Actually standard TATR boxes are usually tight.
                
            cell_img = image.crop(crop_box)
            # Run OCR
            cell.content = ocr_callback(cell_img).strip()
            # print(f"DEBUG: Cell ({cell.row_idx}, {cell.col_idx}): '{cell.content}'")
            
        # 3. Generate LaTeX
        return self._build_latex(cells)

    def _detect_structure(self, image: Image.Image) -> List[TableCell]:
        """Run TATR inference and parse results into TableCell objects"""
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        w, h = image.size
        
        # Preprocess
        # encoding usually handles resizing and normalization
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        
        # Inference
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        # Post-process
        # TATR structure classes:
        # table, table column, table row, table column header, table projected row header, spanning cell
        
        target_sizes = torch.tensor([image.size[::-1]])
        # Lower threshold substantially for debugging
        results = self.processor.post_process_object_detection(outputs, threshold=0.1, target_sizes=target_sizes)[0]
        
        scores = results["scores"]
        labels = results["labels"]
        boxes = results["boxes"]
        
        print(f"DEBUG: TATR Raw Detections count: {len(scores)}")
        
        rows = []
        cols = []
        
        # print("DEBUG: TATR Detections:")
        for score, label, box in zip(scores, labels, boxes):
            box = box.tolist()
            lbl = label.item()
            label_name = self.model.config.id2label[lbl]
            # logger.info(f"TATR Det: {label_name} ({score:.2f})")
            print(f"DEBUG: TATR Det: {label_name} ({score:.2f})")
            
            if label_name in ["table row", "table row header"]:
                rows.append(box)
            elif label_name == "table column":
                cols.append(box)
                
        # Sort rows by Y, Cols by X
        # Row boxes: [x0, y0, x1, y1]. Sort by average Y.
        rows.sort(key=lambda b: (b[1] + b[3])/2)
        
        # Col boxes: [x0, y0, x1, y1]. Sort by average X.
        cols.sort(key=lambda b: (b[0] + b[2])/2)
        
        # logger.info(f"TATR: Found {len(rows)} rows and {len(cols)} columns in image size {image.size}")
        
        if not rows or not cols:
             return []
             
        # Extract cells from intersections
        detected_cells = []
        for r_idx, r_box in enumerate(rows):
            for c_idx, c_box in enumerate(cols):
                # Intersection logic
                # Row spans width, Col spans height.
                # Row Box Y range: [r_y0, r_y1]
                # Col Box X range: [c_x0, c_x1]
                
                # The cell box is effectively the intersection of these ranges
                x0 = c_box[0]
                x1 = c_box[2]
                y0 = r_box[1]
                y1 = r_box[3]
                
                # However, strict intersection might be safer if they overlap coordinates?
                # Usually row box covers full width and col box covers full height.
                # So taking X from col and Y from row is the standard way.
                
                detected_cells.append(TableCell(
                    bbox=[x0, y0, x1, y1],
                    row_idx=r_idx,
                    col_idx=c_idx
                ))
                
        return detected_cells

    def _build_latex(self, cells: List[TableCell]) -> str:
        """Construct LaTeX tabular environment"""
        if not cells:
            return ""
            
        # Determine grid size
        max_row = max(c.row_idx for c in cells)
        max_col = max(c.col_idx for c in cells)
        num_cols = max_col + 1
        
        # Build grid
        grid = [["" for _ in range(num_cols)] for _ in range(max_row + 1)]
        
        for cell in cells:
            if 0 <= cell.row_idx <= max_row and 0 <= cell.col_idx <= max_col:
                grid[cell.row_idx][cell.col_idx] = cell.content
        
        # Generate LaTeX
        col_format = "|" + "c|" * num_cols
        tex = [
            "\\begin{center}",
            f"\\begin{{tabular}}{{{col_format}}}",
            "\\hline"
        ]
        
        for row in grid:
            # Escape & symbols in content is handled by OCR or escape function outside?
            # Assuming content is raw text, valid latex needs separation
            # But wait, OCR callback usually returns LaTeX for math? 
            # If content has &, it breaks tabular. We need to be careful.
            # Ideally OCR callback provides CLEAN text/latex.
            
            # Simple join
            row_tex = " & ".join(row) + " \\\\"
            tex.append(row_tex)
            tex.append("\\hline")
            
        tex.append("\\end{tabular}")
        tex.append("\\end{center}")
        
        return "\n".join(tex)
