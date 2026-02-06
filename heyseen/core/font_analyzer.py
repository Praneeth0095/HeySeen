"""
Font Analyzer Module

Extracts font information (size, weight, style) from PDF using PyMuPDF.
Used for structure detection (distinguishing titles, sections, body text).
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False


@dataclass
class FontInfo:
    """Font information for a text span"""
    size: float  # Font size in points
    weight: int  # Font weight (400=normal, 700=bold)
    is_bold: bool
    is_italic: bool
    font_name: str
    color: Tuple[float, float, float]  # RGB (0-1)


@dataclass
class TextSpan:
    """Text span with font info and position"""
    text: str
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    font: FontInfo


class FontAnalyzer:
    """
    Analyzes font properties in PDF documents.
    
    Extracts detailed font information to help classify text structure:
    - Document titles (large, usually bold)
    - Section headings (medium-large, bold)
    - Subsections (medium, bold)
    - Body text (small, regular)
    - Captions (small, italic)
    """
    
    def __init__(self, pdf_path: str | Path):
        """
        Initialize font analyzer.
        
        Args:
            pdf_path: Path to PDF file
        """
        if not HAS_PYMUPDF:
            raise ImportError(
                "PyMuPDF (fitz) is required for font analysis. "
                "Install with: pip install PyMuPDF"
            )
        
        self.pdf_path = Path(pdf_path)
        self.doc = fitz.open(str(self.pdf_path))
        
    def analyze_page(self, page_num: int) -> List[TextSpan]:
        """
        Extract all text spans with font info from a page.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            List of TextSpan objects
        """
        if page_num >= len(self.doc):
            return []
        
        page = self.doc[page_num]
        spans = []
        
        # Get dictionary containing all text with formatting
        blocks = page.get_text("dict")["blocks"]
        
        for block in blocks:
            if "lines" not in block:
                continue
                
            for line in block["lines"]:
                for span in line["spans"]:
                    font_info = FontInfo(
                        size=span["size"],
                        weight=self._detect_weight(span),
                        is_bold=self._is_bold(span),
                        is_italic=self._is_italic(span),
                        font_name=span["font"],
                        color=span.get("color", (0, 0, 0))
                    )
                    
                    text_span = TextSpan(
                        text=span["text"],
                        bbox=span["bbox"],
                        font=font_info
                    )
                    
                    spans.append(text_span)
        
        return spans
    
    def get_font_statistics(self, page_num: int) -> Dict:
        """
        Get font statistics for a page.
        
        Returns:
            Dict with font size distribution, common styles, etc.
        """
        spans = self.analyze_page(page_num)
        
        if not spans:
            return {}
        
        sizes = [s.font.size for s in spans]
        bold_count = sum(1 for s in spans if s.font.is_bold)
        italic_count = sum(1 for s in spans if s.font.is_italic)
        
        return {
            "total_spans": len(spans),
            "min_size": min(sizes),
            "max_size": max(sizes),
            "median_size": sorted(sizes)[len(sizes) // 2],
            "bold_ratio": bold_count / len(spans),
            "italic_ratio": italic_count / len(spans),
        }
    
    def classify_text_structure(
        self,
        bbox: Tuple[float, float, float, float],
        page_num: int
    ) -> Tuple[str, Dict]:
        """
        Classify text structure based on font properties within a bbox.
        
        Args:
            bbox: Bounding box (x0, y0, x1, y1)
            page_num: Page number
            
        Returns:
            (structure_type, metadata) where structure_type is one of:
            - "title": Document title (largest font, often bold)
            - "section": Section heading (large font, bold)
            - "subsection": Subsection (medium font, bold)
            - "text": Body text (regular size)
            - "caption": Caption text (small, often italic)
        """
        spans = self.analyze_page(page_num)
        
        # Filter spans within bbox
        relevant_spans = [
            s for s in spans
            if self._bbox_overlap(s.bbox, bbox) > 0.5
        ]
        
        if not relevant_spans:
            return "text", {}
        
        # Analyze font properties
        avg_size = sum(s.font.size for s in relevant_spans) / len(relevant_spans)
        is_bold = any(s.font.is_bold for s in relevant_spans)
        is_italic = any(s.font.is_italic for s in relevant_spans)
        
        # Get page font statistics for context
        stats = self.get_font_statistics(page_num)
        median_size = stats.get("median_size", 12)
        
        metadata = {
            "font_size": avg_size,
            "is_bold": is_bold,
            "is_italic": is_italic,
            "rel_size": avg_size / median_size if median_size > 0 else 1.0
        }
        
        # Classification rules
        rel_size = metadata["rel_size"]
        
        # Title: 2x larger than body text, usually bold
        if rel_size > 1.8 and is_bold:
            return "title", metadata
        
        # Section: 1.5x larger, bold
        if rel_size > 1.3 and is_bold:
            return "section", metadata
        
        # Subsection: 1.2x larger, bold
        if rel_size > 1.1 and is_bold:
            return "subsection", metadata
        
        # Caption: smaller than body, often italic
        if rel_size < 0.9 or is_italic:
            return "caption", metadata
        
        # Default to body text
        return "text", metadata
    
    def _detect_weight(self, span: Dict) -> int:
        """Detect font weight from font name"""
        font_name = span["font"].lower()
        
        if any(w in font_name for w in ["bold", "black", "heavy"]):
            return 700
        elif any(w in font_name for w in ["light", "thin"]):
            return 300
        else:
            return 400
    
    def _is_bold(self, span: Dict) -> bool:
        """Check if text is bold"""
        font_name = span["font"].lower()
        flags = span.get("flags", 0)
        
        # Check font name
        if any(w in font_name for w in ["bold", "black", "heavy"]):
            return True
        
        # Check font flags (bit 16 = bold)
        if flags & (1 << 16):
            return True
        
        return False
    
    def _is_italic(self, span: Dict) -> bool:
        """Check if text is italic"""
        font_name = span["font"].lower()
        flags = span.get("flags", 0)
        
        # Check font name
        if any(w in font_name for w in ["italic", "oblique"]):
            return True
        
        # Check font flags (bit 1 = italic)
        if flags & (1 << 1):
            return True
        
        return False
    
    def _bbox_overlap(
        self,
        bbox1: Tuple[float, float, float, float],
        bbox2: Tuple[float, float, float, float]
    ) -> float:
        """Calculate overlap ratio between two bboxes"""
        x0 = max(bbox1[0], bbox2[0])
        y0 = max(bbox1[1], bbox2[1])
        x1 = min(bbox1[2], bbox2[2])
        y1 = min(bbox1[3], bbox2[3])
        
        if x1 < x0 or y1 < y0:
            return 0.0
        
        intersection = (x1 - x0) * (y1 - y0)
        area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
        
        return intersection / area1 if area1 > 0 else 0.0
    
    def close(self):
        """Close PDF document"""
        if self.doc:
            self.doc.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def analyze_pdf_structure(
    pdf_path: str | Path,
    page_num: int = 0
) -> List[Dict]:
    """
    Convenience function to analyze PDF structure.
    
    Args:
        pdf_path: Path to PDF
        page_num: Page number
        
    Returns:
        List of dicts with structure info
    """
    if not HAS_PYMUPDF:
        logging.warning("PyMuPDF not installed. Font analysis disabled.")
        return []
    
    with FontAnalyzer(pdf_path) as analyzer:
        spans = analyzer.analyze_page(page_num)
        
        return [
            {
                "text": s.text,
                "bbox": s.bbox,
                "font_size": s.font.size,
                "is_bold": s.font.is_bold,
                "is_italic": s.font.is_italic,
            }
            for s in spans
        ]
