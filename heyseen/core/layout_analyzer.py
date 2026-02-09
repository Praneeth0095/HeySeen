"""
Layout Analyzer Module

Uses Surya for detecting layout blocks (text, math, figure, table) in PDF pages.
"""

from dataclasses import dataclass
from typing import List, Literal, Tuple, Optional
from enum import Enum

import torch
from PIL import Image
import numpy as np

# Import correct Surya API
from surya.detection import DetectionPredictor, TextDetectionResult
from surya.layout import LayoutPredictor
from surya.foundation import FoundationPredictor


BlockType = Literal["text", "math", "figure", "table", "title", "section", "subsection", "subsubsection", "caption", "list-item"]


@dataclass
class BoundingBox:
    """Bounding box coordinates (normalized 0-1)"""
    x0: float  # left
    y0: float  # top
    x1: float  # right
    y1: float  # bottom
    
    def to_pixels(self, width: int, height: int) -> Tuple[int, int, int, int]:
        """Convert to pixel coordinates"""
        return (
            int(self.x0 * width),
            int(self.y0 * height),
            int(self.x1 * width),
            int(self.y1 * height),
        )
    
    @property
    def area(self) -> float:
        """Calculate normalized area"""
        return (self.x1 - self.x0) * (self.y1 - self.y0)
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get center point"""
        return ((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)


@dataclass
class LayoutBlock:
    """A detected layout block with type and location"""
    
    block_id: int
    block_type: BlockType
    bbox: BoundingBox
    confidence: float
    page_num: int
    
    # Structure metadata (for semantic understanding)
    raw_label: Optional[str] = None  # Original Surya label
    font_size: Optional[float] = None  # Estimated font size (pt)
    is_bold: Optional[bool] = None  # Bold text detection
    is_italic: Optional[bool] = None  # Italic text detection
    
    def __repr__(self) -> str:
        return f"Block({self.block_type}, bbox=[{self.bbox.x0:.2f},{self.bbox.y0:.2f},{self.bbox.x1:.2f},{self.bbox.y1:.2f}], conf={self.confidence:.2f})"


from .model_manager import ModelManager

# Optional font analyzer for enhanced structure detection
try:
    from .font_analyzer import FontAnalyzer, HAS_PYMUPDF
except ImportError:
    FontAnalyzer = None
    HAS_PYMUPDF = False

class LayoutAnalyzer:
    """
    Analyzes page layout using Surya detection models.
    Enhanced with optional font analysis for better structure detection.
    """
    
    def __init__(
        self,
        device: str = "mps",
        batch_size: int = 1,
        verbose: bool = True,
        manager: Optional[ModelManager] = None,
        pdf_path: Optional[str] = None
    ) -> None:
        """
        Initialize layout analyzer.
        
        Args:
            device: Device to run models on
            batch_size: Batch size for inference
            verbose: Print messages
            manager: Model manager instance
            pdf_path: Path to PDF file (for font analysis)
        """
        self.device = device
        self.batch_size = batch_size
        self.verbose = verbose
        self.pdf_path = pdf_path
        
        # Initialize font analyzer if PDF path provided
        self.font_analyzer = None
        if pdf_path and HAS_PYMUPDF and FontAnalyzer:
            try:
                self.font_analyzer = FontAnalyzer(pdf_path)
                if verbose:
                    print(f"✓ Font analyzer enabled for structure detection")
            except Exception as e:
                if verbose:
                    print(f"Warning: Font analyzer failed: {e}")
        
        # Use provided manager or create new (singleton logic inside)
        if manager is None:
            manager = ModelManager.get_instance(device)
            
        if verbose:
            print(f"Loading Surya layout models on {device}...")
        
        # Initialize predictors from Manager
        self.layout_predictor = manager.get_layout_predictor()
        self.det_predictor = manager.get_detection_predictor()
        
        if verbose:
            print(f"✓ Layout & Detection models loaded on {device}")
    
    def detect_layout(
        self,
        image: Image.Image,
        page_num: int = 0,
    ) -> List[LayoutBlock]:
        """
        Detect layout blocks in a single image.
        
        Use Safe Zone filter to remove Headers (Top 5%) and Footers (Bottom 5%).
        """
        # 0. Define Safe Zone (0.05 - 0.95)
        # -------------------------------------------
        SAFE_TOP = 0.05
        SAFE_BOTTOM = 0.95
        
        # 1. Run Layout Prediction (Semantic Regions)
        # -------------------------------------------
        try:
            layout_res = self.layout_predictor([image])[0]
        except Exception as e:
            if self.verbose:
                print(f"Warning: Layout prediction failed: {e}")
            layout_res = None
            
        # 2. Run Text Detection (Lines)
        # -----------------------------
        try:
            det_res = self.det_predictor([image])[0]
        except Exception as e:
            if self.verbose:
                print(f"Warning: Text detection failed: {e}")
            return []

        if not det_res or not det_res.bboxes:
            return []
            
        img_width, img_height = image.size
        blocks = []
        block_counter = 0

        # Helper to convert bbox to normalized BoundingBox
        def to_norm(bbox) -> BoundingBox:
            return BoundingBox(
                x0=bbox[0] / img_width,
                y0=bbox[1] / img_height,
                x1=bbox[2] / img_width,
                y1=bbox[3] / img_height,
            )

        # Helper to check intersection/containment
        # Returns overlapping area
        def get_overlap(box1: BoundingBox, box2: BoundingBox) -> float:
            x_left = max(box1.x0, box2.x0)
            y_top = max(box1.y0, box2.y0)
            x_right = min(box1.x1, box2.x1)
            y_bottom = min(box1.y1, box2.y1)
            
            if x_right < x_left or y_bottom < y_top:
                return 0.0
            
            intersection_area = (x_right - x_left) * (y_bottom - y_top)
            # Return intersection / area of box2 (the text line)
            box2_area = (box2.x1 - box2.x0) * (box2.y1 - box2.y0)
            return intersection_area / box2_area if box2_area > 0 else 0

        # Process Layout Results
        # ----------------------
        
        # Mappings from Surya labels to HeySeen types
        label_map = {
            "Caption": "caption",
            "Footnote": "text",
            "Formula": "math",
            "List-item": "list-item",
            "Page-footer": "text",
            "Page-header": "text",
            "Picture": "figure",
            "Section-header": "section",
            "Table": "table",
            "Text": "text",
            "Title": "title",
        }

        layout_boxes = []
        if layout_res and layout_res.bboxes:
            for b in layout_res.bboxes:
                norm_bbox = to_norm(b.bbox)
                
                # Spatial Filtering (Phase 2.5)
                # Ignore blocks at very Top and Bottom (Headers/Footers)
                # Unless they are specifically essential types (Title, Figure)
                # Note: Titles can be at top, so check label.
                
                label = getattr(b, "label", "Text")
                
                # Filter Logic:
                # 1. Very small height (< 3%) at top/bottom edges
                is_top_edge = norm_bbox.y0 < 0.03
                is_bottom_edge = norm_bbox.y1 > 0.97
                
                # 2. Skip if explicitly labeled as Footer (Header might be valid Title/Section)
                if label in ["Page-footer"]:
                    continue

                # 3. Spatial Skip: If Text/Number at safe zone bounds
                if (is_top_edge or is_bottom_edge) and label == "Text":
                     # Likely page number or running header
                     # Only skip if VERY small (likely noise/page num)
                     if (norm_bbox.y1 - norm_bbox.y0) < 0.015:
                         continue
                
                block_type = label_map.get(label, "text")
                
                layout_boxes.append({
                    "bbox": norm_bbox,
                    "type": block_type,
                    "raw_label": label,
                    "lines": [],
                    "font_size": self._estimate_font_size(norm_bbox),
                })

        # 3. Assign Text Lines to Layout Boxes
        # ------------------------------------
        
        # Pre-assign lines to ALL layout boxes to enable heuristic checks
        for idx, line in enumerate(det_res.bboxes):
             line_bbox = to_norm(line.bbox)
             best_box = None
             best_ov = 0.0
             for lb in layout_boxes:
                 ov = get_overlap(lb["bbox"], line_bbox)
                 if ov > 0.5 and ov > best_ov:
                     best_ov = ov
                     best_box = lb
             
             if best_box:
                 best_box["lines"].append(line_bbox) # Store normalized bbox of line

        # HEURISTIC: Check if "Text" or "Figure" regions are actually Tables
        # Surya sometimes misses tables or calls them Figures/Text.
        for lb in layout_boxes:
            if lb["type"] in ["text", "figure"] and len(lb["lines"]) > 3:
                # Check for grid structure
                if self._is_table_structure(lb["lines"]):
                    if self.verbose:
                         print(f"INFO: Upgrading block {lb['raw_label']} to TABLE based on grid detection.")
                    lb["type"] = "table"
                    lb["raw_label"] = "Table"

        # Identify regions that should be treated as images/blocks
        # Now updated with heuristically detected tables
        block_regions = [lb for lb in layout_boxes if lb["type"] in ["math", "figure", "table"]]
        
        used_line_indices = set()
        
        # First pass: Mark lines belonging to Block Regions as used
        for idx, line in enumerate(det_res.bboxes):
             line_bbox = to_norm(line.bbox)
             for lb in block_regions:
                 if get_overlap(lb["bbox"], line_bbox) > 0.5:
                     used_line_indices.add(idx)
                     break
        
        # Add Block Regions as LayoutBlocks
        for lb in block_regions:
             blocks.append(LayoutBlock(
                block_id=block_counter,
                block_type=lb["type"],
                bbox=lb["bbox"],
                confidence=1.0,
                page_num=page_num,
                raw_label=lb.get("raw_label"),
                font_size=lb.get("font_size")
            ))
             block_counter += 1
             
        # Second pass: Assign remaining lines to Text/Title Layouts or keep as loose lines
        # Only process regions that are NOT captured above
        text_regions = [lb for lb in layout_boxes if lb["type"] not in ["math", "figure", "table"]]
        
        lines_to_process = []
        for idx, line in enumerate(det_res.bboxes):
            if idx in used_line_indices:
                continue
            
            line_bbox = to_norm(line.bbox)
            
            # Find best matching text region
            best_region = None
            best_overlap = 0.0
            
            for region in text_regions:
                ov = get_overlap(region["bbox"], line_bbox)
                if ov > 0.5 and ov > best_overlap:
                    best_overlap = ov
                    best_region = region
            
            # Determine type
            if best_region:
                b_type = best_region["type"]
                # Header/Footer/Page Number heuristic
                # Keep Page-header on first page (often contains Title/Journal info)
                if best_region["raw_label"] in ["Page-header", "Page-footer"]:
                    if page_num == 1 and best_region["raw_label"] == "Page-header":
                        pass # Keep it
                    else:
                        # Skip headers/footers on other pages
                        continue 
            else:
                b_type = "text" # Loose text
                
            # Create block for this line (with structure metadata)
            blocks.append(LayoutBlock(
                block_id=block_counter,
                block_type=b_type,
                bbox=line_bbox,
                confidence=line.confidence if hasattr(line, "confidence") else 1.0,
                page_num=page_num,
                raw_label=best_region["raw_label"] if best_region else None,
                font_size=self._estimate_font_size(line_bbox)
            ))
            block_counter += 1
        
        # Enrich blocks with font info if available
        if self.font_analyzer:
            blocks = self._enrich_with_font_info(blocks, image, page_num)
        
        # AGGRESSIVE TABLE RECOVERY (The "Fragmented Table" Fix)
        # Groups small text/math blocks that look like a grid and merges them into a table
        blocks = self._merge_table_fragments(blocks)
            
        return blocks
    
    def _merge_table_fragments(self, blocks: List[LayoutBlock]) -> List[LayoutBlock]:
        """
        Detects groups of fragmented text blocks that form a table and merges them.
        """
        # Candidates: text/math blocks that are small
        candidates = [b for b in blocks if b.block_type in ["text", "math"]]
        if len(candidates) < 4: return blocks
        
        # Sort by Y
        candidates.sort(key=lambda b: b.bbox.y0)
        
        # Cluster into potential regions (simple vertical proximity)
        clusters = []
        current_cluster = [candidates[0]]
        
        for b in candidates[1:]:
            prev = current_cluster[-1]
            # Gap check
            gap = b.bbox.y0 - prev.bbox.y1
            # If gap is small (< 2% page height) or overlapping, add to cluster
            if gap < 0.02:
                current_cluster.append(b)
            else:
                clusters.append(current_cluster)
                current_cluster = [b]
        clusters.append(current_cluster)
        
        # Analyze each cluster for grid structure
        new_blocks = [b for b in blocks if b not in candidates] # Start with non-candidates
        merged_indices = set()
        
        for cluster in clusters:
            if len(cluster) < 4: 
                # Keep original blocks
                new_blocks.extend(cluster)
                continue
                
            # Convert blocks to bounding boxes for grid check
            bboxes = [b.bbox for b in cluster]
            
            # Use loose grid check
            if self._is_table_structure(bboxes, loose=True):
                # MERGE!
                x0 = min(b.bbox.x0 for b in cluster)
                y0 = min(b.bbox.y0 for b in cluster)
                x1 = max(b.bbox.x1 for b in cluster)
                y1 = max(b.bbox.y1 for b in cluster)
                
                # Check aspect ratio - tables are usually wide
                if (x1-x0) > 0.3: # At least 30% page width
                    merged_block = LayoutBlock(
                        block_id=cluster[0].block_id,
                        block_type="table", # Upgrade to Table
                        bbox=BoundingBox(x0, y0, x1, y1),
                        confidence=1.0,
                        page_num=cluster[0].page_num,
                        raw_label="Table-Fragment-Merged"
                    )
                    new_blocks.append(merged_block)
                    if self.verbose:
                        print(f"INFO: Merged {len(cluster)} blocks into a recovered TABLE.")
                else:
                    new_blocks.extend(cluster)
            else:
                new_blocks.extend(cluster)
                
        # Re-sort blocks just in case
        return sorted(new_blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))

    def _enrich_with_font_info(
        self,
        blocks: List[LayoutBlock],
        image: Image.Image,
        page_num: int
    ) -> List[LayoutBlock]:
        """
        Enrich layout blocks with font information from PDF.
        
        Updates:
        - font_size: Real font size from PDF (more accurate)
        - is_bold: Detected from font flags
        - is_italic: Detected from font flags
        """
        try:
            # First pass: Extract raw font data
            for block in blocks:
                # Convert normalized bbox to pixel coordinates
                img_width, img_height = image.size
                x0, y0, x1, y1 = block.bbox.to_pixels(img_width, img_height)
                pixel_bbox = (x0, y0, x1, y1)
                
                # Get metadata
                _, metadata = self.font_analyzer.classify_text_structure(
                    pixel_bbox, page_num
                )
                
                if metadata:
                    block.font_size = metadata.get("font_size", block.font_size)
                    block.is_bold = metadata.get("is_bold", False)
                    block.is_italic = metadata.get("is_italic", False)
            
            # Second pass: Calculate relative font statistics
            valid_sizes = [b.font_size for b in blocks if b.font_size and b.block_type == "text"]
            if valid_sizes:
                import statistics
                median_size = statistics.median(valid_sizes)
                if self.verbose:
                    print(f"INFO: Page {page_num} Median Font Size: {median_size:.1f}pt")
                
                # Re-classify based on relative offsets
                for block in blocks:
                    if not block.font_size or not block.block_type in ["text", "section", "title"]: continue
                    
                    # Title: > 1.5x median OR (> 1.2x median AND Bold)
                    # Section: > 1.15x median AND Bold
                    # Note: We are conservative to avoid false positives
                    rel_size = block.font_size / median_size
                    
                    # Heuristic updates:
                    # 1. Be stricter about Title (must be significantly larger or bold+large)
                    # 2. Be more careful with Section vs Text (avoid classifying short bold phrases as section if they continue a sentence)
                    
                    # Revised Heuristics
                    
                    if rel_size > 2.0: # Very large
                         block.block_type = "title"
                    elif rel_size > 1.4: # Large
                         # If bold, definitely title/section. If not, maybe just large text?
                         block.block_type = "section" if block.is_bold else "title"
                    elif rel_size > 1.2 and block.is_bold:
                         block.block_type = "section"
                    elif rel_size > 1.1 and block.is_bold:
                         block.block_type = "subsection"
                    elif block.is_bold and rel_size > 1.05:
                         block.block_type = "subsubsection"
                    elif block.is_bold and rel_size > 0.95:
                         # Likely a run-in heading or paragraph title
                         # We'll allow it as subsubsection if it's start of line?
                         # For now, treat as subsubsection to capture structure
                         block.block_type = "subsubsection"
        except Exception as e:
            if self.verbose:
                print(f"Warning: Font enrichment failed: {e}")
        
        return blocks
    
    def _estimate_font_size(self, bbox: BoundingBox) -> float:
        """
        Estimate font size from bounding box height.
        
        Font size (pt) ≈ bbox_height (normalized) * page_height (px) / 4
        Assumes typical line height is ~1.2-1.5x font size.
        
        Args:
            bbox: Normalized bounding box
            
        Returns:
            Estimated font size in points
        """
        height = bbox.y1 - bbox.y0
        # Typical page height ~1000px @ 150 DPI
        # height=0.02 (2% page) ≈ 20px ≈ 15pt font
        estimated_pt = height * 750  # Rough approximation
        return round(estimated_pt, 1)
    
    def _classify_block(self, bbox: BoundingBox, image: Image.Image) -> BlockType:
        """
        Classify block type based on heuristics.
        TODO: Replace with proper classifier in Phase 2.
        
        Args:
            bbox: Bounding box
            image: Source image
            
        Returns:
            Predicted block type
        """
        # Simple heuristics for now:
        # - Small area at top = title
        # - Very wide aspect ratio = text
        # - Square/tall aspect ratio = figure
        # - TODO: Use ML classifier later
        
        width = bbox.x1 - bbox.x0
        height = bbox.y1 - bbox.y0
        aspect_ratio = width / height if height > 0 else 1.0
        
        # Top 15% of page
        if bbox.y0 < 0.15 and bbox.area < 0.3:
            return "title"
        
        # Very wide and short
        if aspect_ratio > 5.0:
            return "caption"
        
        # Square or tall (likely figure)
        if 0.5 < aspect_ratio < 1.5 and bbox.area > 0.1:
            return "figure"
        
        # Default to text
        return "text"
    
    def _is_table_structure(self, lines: List[BoundingBox], loose: bool = False) -> bool:
        """
        Check if a set of lines forms a table-like grid structure.
        """
        if len(lines) < 4: return False # Too few lines to be a table
        
        # simple clustering by Y to find rows
        lines_sorted = sorted(lines, key=lambda b: b.y0)
        rows = []
        current_row = [lines_sorted[0]]
        
        for line in lines_sorted[1:]:
            # Overlap in Y?
            prev = current_row[-1]
            ov_y = min(prev.y1, line.y1) - max(prev.y0, line.y0)
            h = min(prev.y1 - prev.y0, line.y1 - line.y0)
            
            # Loose mode is more lenient with alignment
            threshold = 0.3 if loose else 0.5
            
            if h > 0 and (ov_y / h) > threshold:
                current_row.append(line)
            else:
                rows.append(current_row)
                current_row = [line]
        rows.append(current_row)
        
        # Check if we have multiple columns
        multi_col_rows = 0
        for row in rows:
            # Check horizontal separation
            if len(row) > 1:
                # Sort by X
                row_x = sorted(row, key=lambda b: b.x0)
                # Check gaps
                valid_gaps = 0
                for i in range(len(row_x)-1):
                     if row_x[i+1].x0 > row_x[i].x1: # Non-overlapping
                         valid_gaps += 1
                if valid_gaps > 0:
                    multi_col_rows += 1
        
        # Rule: At least 30% of rows have multiple columns
        # In loose mode, maybe just 20%?
        ratio = 0.5 if loose else 0.3
        
        if len(rows) > 1 and (multi_col_rows / len(rows)) > ratio:
            # Additional check for loose mode: density
            if loose:
                # Tables are usually dense
                return True
            return True
            
        return False

    def sort_reading_order(self, blocks: List[LayoutBlock]) -> List[LayoutBlock]:
        """
        Sort blocks in reading order with smart column detection.
        
        Strategy:
        1. Separate headers/footers (wide, spanning blocks)
        2. Detect multi-column layout in body
        3. Group blocks into columns
        4. Sort each column top-to-bottom
        
        This handles mixed layouts (title + 2-column body).
        """
        if not blocks:
            return []
            
        # Filter noise (extremely small blocks) - reduced threshold
        valid_blocks = [b for b in blocks if b.bbox.area > 0.0001] 
        if not valid_blocks:
            return blocks

        # Separate header/footer from body
        top_spanning = []
        bottom_spanning = []
        body_candidates = []
        
        for b in valid_blocks:
            width = b.bbox.x1 - b.bbox.x0
            is_wide = width > 0.8  # Must be very wide to be a header spanner
            is_top = b.bbox.y1 < 0.10
            is_bottom = b.bbox.y0 > 0.93
            
            if is_top or (is_wide and b.bbox.y0 < 0.08): 
                top_spanning.append(b)
            elif is_bottom:
                bottom_spanning.append(b)
            else:
                body_candidates.append(b)
                
        # Sort spanning blocks by Y
        top_spanning.sort(key=lambda b: b.bbox.y0)
        bottom_spanning.sort(key=lambda b: b.bbox.y0)
        
        if not body_candidates:
             return top_spanning + bottom_spanning
             
        # Detect columns and sort
        body_sorted = self._sort_with_column_detection(body_candidates)
        
        # Final pass: Merge horizontally aligned blocks that are very close
        # This fixes split section numbers (e.g. "1" ... "Title") by combining them
        # into a single region for OCR, helping Texify see the full context.
        final_sorted = self._merge_aligned_blocks(top_spanning + body_sorted + bottom_spanning)
            
        return final_sorted
    
    def _merge_aligned_blocks(self, blocks: List[LayoutBlock]) -> List[LayoutBlock]:
        """
        Merge blocks that are horizontally adjacent and on the same line.
        This heals localized segmentation fragmentation (e.g. "1" split from "Title").
        """
        if not blocks:
            return []
            
        merged_blocks = []
        current_block = blocks[0]
        
        for next_block in blocks[1:]:
            # Check for vertical alignment (Overlap > 50%)
            y_overlap = min(current_block.bbox.y1, next_block.bbox.y1) - max(current_block.bbox.y0, next_block.bbox.y0)
            h1 = current_block.bbox.y1 - current_block.bbox.y0
            h2 = next_block.bbox.y1 - next_block.bbox.y0
            min_h = min(h1, h2)
            
            is_same_line = (y_overlap / min_h) > 0.4 if min_h > 0 else False
            
            # Check horizontal proximity (Gap < 1% of page width)
            # Standard column gap is ~2%+. Word gap is <1%.
            gap = next_block.bbox.x0 - current_block.bbox.x1
            is_close = -0.005 < gap < 0.015  # Allow slight overlap or small gap
            
            # Check type compatibility (don't merge Figure with Text, but Text+Section is ok to heal)
            # Actually, if we merge, we should probably take the 'dominant' type or default to text/section.
            is_compatible = (
                current_block.block_type in ["text", "section", "title", "list-item", "caption"] and 
                next_block.block_type in ["text", "section", "title", "list-item", "caption"]
            )
            
            if is_same_line and is_close and is_compatible:
                # Merge!
                # 1. Union BBox
                new_bbox = BoundingBox(
                    x0=min(current_block.bbox.x0, next_block.bbox.x0),
                    y0=min(current_block.bbox.y0, next_block.bbox.y0),
                    x1=max(current_block.bbox.x1, next_block.bbox.x1),
                    y1=max(current_block.bbox.y1, next_block.bbox.y1)
                )
                
                # 2. Update Metadata
                # Prefer "section"/"title" label if present
                new_type = next_block.block_type if next_block.block_type in ["section", "title"] else current_block.block_type
                new_label = next_block.raw_label if next_block.raw_label in ["Section-header", "Title"] else current_block.raw_label
                
                # Create merged block (preserve ID of first)
                current_block = LayoutBlock(
                    block_id=current_block.block_id,
                    block_type=new_type,
                    bbox=new_bbox,
                    confidence=max(current_block.confidence, next_block.confidence),
                    page_num=current_block.page_num,
                    raw_label=new_label,
                    font_size=max(current_block.font_size or 0, next_block.font_size or 0) or None,
                    is_bold=current_block.is_bold or next_block.is_bold
                )
            else:
                # Push current and start new
                merged_blocks.append(current_block)
                current_block = next_block
                
        merged_blocks.append(current_block)
        return merged_blocks
    
    def _sort_with_column_detection(self, blocks: List[LayoutBlock]) -> List[LayoutBlock]:
        """
        Sort blocks with intelligent column detection.
        Checks for valid gutter to confirm column separation.
        """
        if not blocks:
            return []
        
        # Collect X-coordinates (left edge) to detect column boundaries
        x_coords = sorted([b.bbox.x0 for b in blocks])
        
        # Find potential splits based on left-edge distribution
        potential_splits = []
        if len(x_coords) > 1:
            for i in range(len(x_coords) - 1):
                gap = x_coords[i + 1] - x_coords[i]
                if gap > 0.02: # 2% indentation threshold
                     split_x = (x_coords[i] + x_coords[i + 1]) / 2
                     potential_splits.append((gap, split_x))
        
        potential_splits.sort(key=lambda x: x[0], reverse=True)
        
        best_split = None
        for gap, split_x in potential_splits:
            # VALIDATION: Check if this split actually separates content
            # A valid column split should NOT have many blocks crossing it
            crossing_blocks = 0
            for b in blocks:
                if b.bbox.x0 < split_x < b.bbox.x1:
                    crossing_blocks += 1
            
            # If more than 10% of blocks cross the line, it's not a column split
            # (Allows for a few outliers like titles or figures spanning columns)
            if crossing_blocks < len(blocks) * 0.1:
                best_split = split_x
                break
        
        if best_split:
            # Assign blocks to columns
            left_col = [b for b in blocks if b.bbox.x1 <= best_split] # Mostly Left
            # Crossing blocks usually go to the column where their center is, 
            # or handle specially. For simplicity, assign by center.
            
            left_col = []
            right_col = []
            for b in blocks:
                center_x = (b.bbox.x0 + b.bbox.x1) / 2
                if center_x < best_split:
                     left_col.append(b)
                else:
                     right_col.append(b)
            
            # Check if this is truly a 2-column layout (content balanced-ish)
            if len(left_col) >= 1 and len(right_col) >= 1:
                # Sort each column by Y, then X
                left_sorted = sorted(left_col, key=lambda b: (b.bbox.y0, b.bbox.x0))
                right_sorted = sorted(right_col, key=lambda b: (b.bbox.y0, b.bbox.x0))
                
                # Check for vertical overlap between columns (Text Flow Check)
                # If Left column covers Y=[0.1, 0.9] and Right covers Y=[0.1, 0.9], it's 2-col.
                # If Left covers Y=[0.1, 0.5] and Right covers Y=[0.5, 0.9], it's FALSE column 
                # (just top-left paragraph and bottom-right paragraph?). No, that's fine.
                
                return left_sorted + right_sorted
        
        # Single column: sort by Y then X
        return sorted(blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))
    
    def _xy_cut(self, blocks: List[LayoutBlock], depth: int = 0, max_depth: int = 5) -> List[LayoutBlock]:
        """
        Recursive XY-Cut algorithm.
        
        Args:
            blocks: Blocks to sort
            depth: Current recursion depth
            max_depth: Maximum recursion depth
            
        Returns:
            Sorted blocks
        """
        if not blocks or depth >= max_depth:
            # Base case: sort by Y then X
            return sorted(blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))
        
        if len(blocks) == 1:
            return blocks
        
        # Calculate gaps in X and Y directions
        x_gap, x_pos = self._find_largest_gap(blocks, axis='x')
        y_gap, y_pos = self._find_largest_gap(blocks, axis='y')
        
        # Threshold for significant gap (Reduced to 2% to catch narrow column gaps)
        gap_threshold = 0.02
        
        # Choose cut direction (larger gap wins)
        if x_gap > gap_threshold and x_gap >= y_gap:
            # Vertical cut (split into left/right)
            left = [b for b in blocks if (b.bbox.x0 + b.bbox.x1) / 2 < x_pos]
            right = [b for b in blocks if (b.bbox.x0 + b.bbox.x1) / 2 >= x_pos]
            return self._xy_cut(left, depth + 1, max_depth) + self._xy_cut(right, depth + 1, max_depth)
        elif y_gap > gap_threshold:
            # Horizontal cut (split into top/bottom)
            top = [b for b in blocks if (b.bbox.y0 + b.bbox.y1) / 2 < y_pos]
            bottom = [b for b in blocks if (b.bbox.y0 + b.bbox.y1) / 2 >= y_pos]
            return self._xy_cut(top, depth + 1, max_depth) + self._xy_cut(bottom, depth + 1, max_depth)
        else:
            # No significant gap, sort by reading order (top-to-bottom, left-to-right)
            return sorted(blocks, key=lambda b: (b.bbox.y0, b.bbox.x0))
    
    def _find_largest_gap(self, blocks: List[LayoutBlock], axis: str) -> Tuple[float, float]:
        """
        Find the largest gap between blocks along an axis.
        
        Args:
            blocks: List of blocks
            axis: 'x' for horizontal gap, 'y' for vertical gap
            
        Returns:
            (gap_size, gap_position)
        """
        if axis == 'x':
            # Sort by horizontal position
            sorted_blocks = sorted(blocks, key=lambda b: b.bbox.x0)
            positions = [(b.bbox.x0, b.bbox.x1) for b in sorted_blocks]
        else:  # axis == 'y'
            # Sort by vertical position
            sorted_blocks = sorted(blocks, key=lambda b: b.bbox.y0)
            positions = [(b.bbox.y0, b.bbox.y1) for b in sorted_blocks]
        
        # Find gaps
        max_gap = 0.0
        gap_pos = 0.5  # Default to middle
        
        for i in range(len(positions) - 1):
            gap_start = positions[i][1]  # End of current block
            gap_end = positions[i + 1][0]  # Start of next block
            gap = gap_end - gap_start
            
            if gap > max_gap:
                max_gap = gap
                gap_pos = (gap_start + gap_end) / 2
        
        return max_gap, gap_pos

    def batch_detect(
        self,
        images: List[Image.Image],
        start_page_num: int = 0,
    ) -> List[List[LayoutBlock]]:
        """
        Detect layout in multiple images (batch processing).
        
        Args:
            images: List of PIL Images
            start_page_num: Starting page number
            
        Returns:
            List of block lists (one per image)
        """
        all_blocks = []
        
        for i, image in enumerate(images):
            blocks = self.detect_layout(image, page_num=start_page_num + i)
            all_blocks.append(blocks)
        
        return all_blocks
    
    def visualize_layout(
        self,
        image: Image.Image,
        blocks: List[LayoutBlock],
        show_labels: bool = True,
    ) -> Image.Image:
        """
        Draw bounding boxes on image for visualization.
        
        Args:
            image: Source image
            blocks: Detected blocks
            show_labels: Show block type labels
            
        Returns:
            Annotated image
        """
        from PIL import ImageDraw, ImageFont
        
        img = image.copy()
        draw = ImageDraw.Draw(img)
        
        # Color mapping for block types
        colors = {
            "text": (0, 255, 0),          # Green
            "math": (255, 0, 0),          # Red
            "figure": (0, 0, 255),        # Blue
            "table": (255, 165, 0),       # Orange
            "title": (255, 0, 255),       # Magenta
            "section": (128, 0, 128),     # Purple
            "subsection": (200, 100, 200), # Light Purple
            "caption": (0, 255, 255),     # Cyan
            "list-item": (255, 255, 0),   # Yellow
        }
        
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except:
            font = ImageFont.load_default()
        
        for block in blocks:
            color = colors.get(block.block_type, (128, 128, 128))
            x0, y0, x1, y1 = block.bbox.to_pixels(img.width, img.height)
            
            # Draw rectangle
            draw.rectangle([(x0, y0), (x1, y1)], outline=color, width=3)
            
            # Draw label
            if show_labels:
                label = f"{block.block_type} ({block.confidence:.2f})"
                draw.text((x0 + 5, y0 + 5), label, fill=color, font=font)
        
        return img


def analyze_layout(
    image: Image.Image,
    device: str = "mps",
    verbose: bool = False,
) -> List[LayoutBlock]:
    """
    Convenience function to analyze layout of a single image.
    
    Args:
        image: PIL Image
        device: Device to run on
        verbose: Print messages
        
    Returns:
        List of detected blocks in reading order
    """
    analyzer = LayoutAnalyzer(device=device, verbose=verbose)
    blocks = analyzer.detect_layout(image)
    return analyzer.sort_reading_order(blocks)
