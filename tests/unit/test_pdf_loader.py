"""
Tests for PDF Loader
"""

from pathlib import Path
import pytest
from heyseen.core.pdf_loader import PDFLoader, load_pdf


def test_pdf_loader_placeholder():
    """Placeholder test - will add real tests with sample PDFs"""
    # TODO: Add sample PDF to tests/data/
    # For now, just test that the module imports correctly
    assert PDFLoader is not None
    assert load_pdf is not None


# TODO: Add these tests after adding sample PDFs
# def test_load_single_page():
#     loader = PDFLoader("tests/data/sample.pdf")
#     page = loader.load_single_page(0)
#     assert page.page_num == 0
#     assert page.image is not None
#
# def test_load_all_pages():
#     pages = load_pdf("tests/data/sample.pdf", dpi=150)
#     assert len(pages) > 0
#     assert all(p.dpi == 150 for p in pages)
