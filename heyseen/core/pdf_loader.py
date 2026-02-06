"""
PDF Loader Module

Loads PDF files and extracts pages as PIL Images for processing.
"""

from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass

import pypdfium2 as pdfium
from PIL import Image
from tqdm import tqdm


@dataclass
class PageImage:
    """Container for a single PDF page image with metadata"""
    
    page_num: int
    image: Image.Image
    width: int
    height: int
    dpi: int


@dataclass
class PDFMetadata:
    """PDF document metadata"""
    
    title: Optional[str]
    author: Optional[str]
    page_count: int
    file_size: int


class PDFLoader:
    """
    Loads PDF files and converts pages to images.
    
    Example:
        >>> loader = PDFLoader("paper.pdf")
        >>> metadata = loader.get_metadata()
        >>> pages = loader.load_pages(dpi=300)
    """
    
    def __init__(self, pdf_path: str | Path, verbose: bool = True) -> None:
        """
        Initialize PDF loader.
        
        Args:
            pdf_path: Path to PDF file
            verbose: Show progress bars
        """
        self.pdf_path = Path(pdf_path)
        self.verbose = verbose
        
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {self.pdf_path}")
        
        self._pdf = pdfium.PdfDocument(str(self.pdf_path))
    
    def get_metadata(self) -> PDFMetadata:
        """Extract PDF metadata"""
        metadata_dict = self._pdf.get_metadata_dict()
        
        return PDFMetadata(
            title=metadata_dict.get("Title"),
            author=metadata_dict.get("Author"),
            page_count=len(self._pdf),
            file_size=self.pdf_path.stat().st_size,
        )
    
    def load_pages(
        self, 
        dpi: int = 300,
        start_page: int = 0,
        end_page: Optional[int] = None,
    ) -> List[PageImage]:
        """
        Load PDF pages as images.
        
        Args:
            dpi: Resolution for rendering (default 300)
            start_page: First page to load (0-indexed)
            end_page: Last page to load (exclusive), None = all pages
            
        Returns:
            List of PageImage objects
        """
        if end_page is None:
            end_page = len(self._pdf)
        
        pages = []
        page_range = range(start_page, min(end_page, len(self._pdf)))
        
        iterator = tqdm(page_range, desc="Loading pages") if self.verbose else page_range
        
        for page_num in iterator:
            page = self._pdf[page_num]
            
            # Render page to PIL Image
            pil_image = page.render(
                scale=dpi / 72,  # pypdfium2 uses 72 DPI base
                rotation=0,
            ).to_pil()
            
            pages.append(PageImage(
                page_num=page_num,
                image=pil_image,
                width=pil_image.width,
                height=pil_image.height,
                dpi=dpi,
            ))
        
        return pages
    
    def load_single_page(self, page_num: int, dpi: int = 300) -> PageImage:
        """Load a single page by number"""
        if page_num < 0 or page_num >= len(self._pdf):
            raise ValueError(f"Invalid page number: {page_num} (total pages: {len(self._pdf)})")
        
        pages = self.load_pages(dpi=dpi, start_page=page_num, end_page=page_num + 1)
        return pages[0]
    
    def __len__(self) -> int:
        """Return number of pages"""
        return len(self._pdf)
    
    def __repr__(self) -> str:
        return f"PDFLoader('{self.pdf_path}', pages={len(self._pdf)})"
    
    def close(self) -> None:
        """Close PDF document"""
        self._pdf.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def load_pdf(pdf_path: str | Path, dpi: int = 300, verbose: bool = True, pages: str = None) -> List[PageImage]:
    """
    Convenience function to load pages from a PDF.
    
    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for rendering
        verbose: Show progress bars
        pages: Page range string (e.g. "1-5", "10", "1-")
        
    Returns:
        List of PageImage objects
    """
    with PDFLoader(pdf_path, verbose=verbose) as loader:
        start_page = 0
        end_page = None
        
        if pages:
            if "-" in pages:
                parts = pages.split("-")
                start_page = int(parts[0]) - 1 # Convert to 0-indexed
                if parts[1]:
                    end_page = int(parts[1])
            else:
                s = int(pages) - 1
                start_page = s
                end_page = s + 1
                
        return loader.load_pages(dpi=dpi, start_page=start_page, end_page=end_page)
