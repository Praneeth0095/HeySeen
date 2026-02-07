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
import logging

from .model_manager import ModelManager

logger = logging.getLogger(__name__)

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
            logger.warning("Table Transformer model not available.")

    def process_table(self, image: Image.Image, ocr_callback: Callable[[Image.Image], str]) -> str:
        """
        Process a table image Crop -> LaTeX code.
        
        Args:
            image: PIL Image of the table region
            ocr_callback: Function that takes an image crop and returns text content
            
        Returns:
            LaTeX tabular code, or "" if not a valid table.
        """
        if not self.model:
            return "% Table recognition unavailable (Model failed to load)\n"
        
        # 1. Structure Recognition
        cells = self._detect_structure(image)
        if not cells:
            # logger.info("TATR: No table structure detected.")
            return "" 
            
        logger.info(f"TATR: Processing {len(cells)} cells...")
        
        # 2. OCR Content for each cell
        cells_with_content = []
        for i, cell in enumerate(cells):
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
            
            # Pad crop significantly to capture edges
            pad = 12
            padded_box = (
                max(0, crop_box[0] - pad),
                max(0, crop_box[1] - pad),
                min(image.width, crop_box[2] + pad),
                min(image.height, crop_box[3] + pad)
            )
            
            cell_img = image.crop(padded_box)
            # Run OCR
            cell.content = ocr_callback(cell_img).strip()
            cells_with_content.append(cell)
            
        # 3. Post-OCR Validation (Heuristic: Reject text paragraphs masquerading as tables)
        if self._is_false_positive_table(cells_with_content):
            logger.info("TATR: Rejected table based on content heuristics (likely paragraph).")
            return ""

        # 4. Generate LaTeX
        return self._build_latex(cells_with_content)

    def _is_false_positive_table(self, cells: List[TableCell]) -> bool:
        """
        Check if the detected table is likely just a text paragraph.
        """
        if not cells: return True
        
        # Filter empty cells
        filled_cells = [c for c in cells if c.content]
        if not filled_cells: return True
        
        total_filled = len(filled_cells)
        
        # Heuristic 1: Lowercase start ratio
        lowercase_starts = 0
        for cell in filled_cells:
            # Check first char
            text = cell.content
            # Skip if math or special chars (rough check)
            clean_text = ''.join(c for c in text if c.isalpha())
            if clean_text:
                if clean_text[0].islower():
                    lowercase_starts += 1
        
        lowercase_ratio = lowercase_starts / total_filled
        
        # Threshold: If > 40% of cells start with lowercase, it's suspicious.
        # Exceptions: If very few cells (e.g. 2x2 matrix), heuristics might fail, but usually ok.
        if lowercase_ratio > 0.40:
             return True
             
        # Heuristic 2: 1-Column Table Rejection
        columns_indices = set(c.col_idx for c in cells)
        rows_indices = set(c.row_idx for c in cells)
        if len(columns_indices) <= 1 and len(rows_indices) > 2:
            return True
            
        return False

    def _detect_structure(self, image: Image.Image) -> List[TableCell]:
        """Run TATR inference and parse results into TableCell objects"""
        # Ensure RGB for model compatibility
        if image.mode != "RGB":
            image = image.convert("RGB")
            
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            
        target_sizes = torch.tensor([image.size[::-1]])
        
        # Threshold: 0.5 is standard.
        results = self.processor.post_process_object_detection(outputs, threshold=0.5, target_sizes=target_sizes)[0]
        
        scores = results["scores"]
        labels = results["labels"]
        boxes = results["boxes"]
        
        rows = []
        cols = []
        
        for score, label, box in zip(scores, labels, boxes):
            box = box.tolist()
            lbl = label.item()
            label_name = self.model.config.id2label[lbl]
            
            if label_name in ["table row", "table row header"]:
                rows.append(box)
            elif label_name == "table column":
                cols.append(box)
                
        # Sort rows by Y, Cols by X
        rows.sort(key=lambda b: (b[1] + b[3])/2)
        cols.sort(key=lambda b: (b[0] + b[2])/2)
        
        if not rows or not cols:
             return []
             
        detected_cells = []
        for r_idx, r_box in enumerate(rows):
            for c_idx, c_box in enumerate(cols):
                # Intersection
                x0 = c_box[0]
                x1 = c_box[2]
                y0 = r_box[1]
                y1 = r_box[3]
                
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
            
        max_row = max(c.row_idx for c in cells)
        max_col = max(c.col_idx for c in cells)
        num_cols = max_col + 1
        
        grid = [["" for _ in range(num_cols)] for _ in range(max_row + 1)]
        
        for cell in cells:
            if 0 <= cell.row_idx <= max_row and 0 <= cell.col_idx <= max_col:
                grid[cell.row_idx][cell.col_idx] = cell.content
        
        col_format = "|" + "c|" * num_cols
        tex = [
            "\\begin{center}",
            f"\\begin{{tabular}}{{{col_format}}}",
            "\\hline"
        ]
        
        for row in grid:
            row_tex = " & ".join(row) + " \\\\"
            tex.append(row_tex)
            tex.append("\\hline")
            
        tex.append("\\end{tabular}")
        tex.append("\\end{center}")
        
        return "\n".join(tex)
