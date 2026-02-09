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
        
        # 1. Structure Recognition (now returns list of tables)
        tables_cells = self._detect_tables(image)
        if not tables_cells:
            return "" 
            
        logger.info(f"TATR: Detected {len(tables_cells)} distinct tables.")
        
        latex_outputs = []
        
        for idx, cells in enumerate(tables_cells):
            logger.info(f"TATR: Processing Table {idx+1} ({len(cells)} cells)...")
            
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
                # Ensure we don't pad outside image
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
            
            # 3. Post-OCR Validation
            if self._is_false_positive_table(cells_with_content):
                logger.info(f"TATR: Rejected Table {idx+1} based on content heuristics.")
                continue

            # 4. Generate LaTeX
            latex_outputs.append(self._build_latex(cells_with_content))

        return "\n\n".join(latex_outputs)

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
        valid_cells_count = 0
        
        for cell in filled_cells:
            text = cell.content.strip()
            
            # Skip if it looks like a LaTeX command or math
            if any(sym in text for sym in ['\\', '$', '=', '^', '_', '{', '}']):
                valid_cells_count += 1
                continue
                
            # Check first char
            clean_text = ''.join(c for c in text if c.isalpha())
            if clean_text:
                if clean_text[0].islower():
                    lowercase_starts += 1
                valid_cells_count += 1
        
        if valid_cells_count == 0:
            return False # All were math/empty, assume valid table
            
        lowercase_ratio = lowercase_starts / valid_cells_count
        
        # Threshold: Relaxed to 80% to handle descriptions in tables
        # or specific languages where lowercase is common.
        if lowercase_ratio > 0.80:
             return True
             
        # Heuristic 2: 1-Column Table Rejection
        columns_indices = set(c.col_idx for c in cells)
        rows_indices = set(c.row_idx for c in cells)
        if len(columns_indices) <= 1 and len(rows_indices) > 2:
            return True
            
        return False

    def _detect_tables(self, image: Image.Image) -> List[List[TableCell]]:
        """Run TATR inference and parse results into List of Tables (each is List[TableCell])"""
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
        
        # 1. Collect Objects
        table_boxes = []
        rows = []
        cols = []
        
        for score, label, box in zip(scores, labels, boxes):
            box = box.tolist()
            lbl = label.item()
            label_name = self.model.config.id2label[lbl]
            
            if label_name == "table":
                table_boxes.append(box)
            elif label_name in ["table row", "table row header"]:
                rows.append(box)
            elif label_name == "table column":
                cols.append(box)
                
        # Sort objects
        rows.sort(key=lambda b: (b[1] + b[3])/2)
        cols.sort(key=lambda b: (b[0] + b[2])/2)
        table_boxes.sort(key=lambda b: b[1])
        
        # 2. Define Table Regions
        # If no table object detected, try to cluster rows to find implicit tables
        if not table_boxes and rows:
             # Sort rows by Y
             rows.sort(key=lambda b: (b[1] + b[3])/2)
             
             clusters = []
             if rows:
                 current_cluster = [rows[0]]
                 
                 for i in range(1, len(rows)):
                     curr_box = rows[i]
                     prev_box = rows[i-1]
                     
                     # Calculate gap
                     gap = curr_box[1] - prev_box[3]
                     prev_height = prev_box[3] - prev_box[1]
                     
                     # Heuristic: Gap > 1.5x height OR > 50px implies separate table
                     if gap > 1.5 * prev_height or gap > 50: 
                         clusters.append(current_cluster)
                         current_cluster = [curr_box]
                     else:
                         current_cluster.append(curr_box)
                 clusters.append(current_cluster)
             
             # Create table boxes from clusters
             for cluster in clusters:
                 # Find bounding box of cluster rows
                 y0 = min(r[1] for r in cluster)
                 y1 = max(r[3] for r in cluster)
                 # Use full width to ensure we catch columns
                 table_boxes.append([0, max(0, y0 - 10), image.width, min(image.height, y1 + 10)])
                 
        if not table_boxes:
            # Fallback if no rows either (or empty file)
            table_boxes = [[0, 0, image.width, image.height]]
            
        # 3. Process each table region
        all_tables_cells = []
        
        for t_box in table_boxes:
            # Filter rows/cols that belong to this table
            # Check overlap > 50%
            t_rows = [r for r in rows if self._is_contained(r, t_box)]
            t_cols = [c for c in cols if self._is_contained(c, t_box)]
            
            if not t_rows or not t_cols:
                continue
                
            # Re-sort for this table
            t_rows.sort(key=lambda b: (b[1] + b[3])/2)
            t_cols.sort(key=lambda b: (b[0] + b[2])/2)
            
            # Build Cells (Grid Intersection)
            cells = []
            for r_idx, r_box in enumerate(t_rows):
                for c_idx, c_box in enumerate(t_cols):
                    # Intersection logic
                    x0 = max(c_box[0], r_box[0])
                    y0 = max(c_box[1], r_box[1])
                    x1 = min(c_box[2], r_box[2])
                    y1 = min(c_box[3], r_box[3])
                    
                    # Check if valid intersection
                    if x1 > x0 and y1 > y0:
                        cells.append(TableCell(
                            bbox=[x0, y0, x1, y1],
                            row_idx=r_idx,
                            col_idx=c_idx
                        ))
            
            if cells:
                all_tables_cells.append(cells)
                
        # Fallback: If no tables produced but we had a valid table box from surya (implied),
        # And we have rows/cols.
        # This handles case where detection of 'table' failed but rows/cols were found.
        if not all_tables_cells and not table_boxes and rows and cols:
             cells = []
             for r_idx, r_box in enumerate(rows):
                for c_idx, c_box in enumerate(cols):
                    x0 = max(c_box[0], r_box[0])
                    y0 = max(c_box[1], r_box[1])
                    x1 = min(c_box[2], r_box[2])
                    y1 = min(c_box[3], r_box[3])
                    if x1 > x0 and y1 > y0:
                        cells.append(TableCell(bbox=[x0, y0, x1, y1], row_idx=r_idx, col_idx=c_idx))
             if cells:
                 all_tables_cells.append(cells)

        return all_tables_cells

    def _is_contained(self, box, container, threshold=0.5):
        """Check if box is largely inside container query"""
        # box, container: [x0, y0, x1, y1]
        x0 = max(box[0], container[0])
        y0 = max(box[1], container[1])
        x1 = min(box[2], container[2])
        y1 = min(box[3], container[3])
        
        if x1 <= x0 or y1 <= y0:
            return False
            
        intersection_area = (x1 - x0) * (y1 - y0)
        box_area = (box[2] - box[0]) * (box[3] - box[1])
        if box_area <= 0: return False
        
        return (intersection_area / box_area) > threshold

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
