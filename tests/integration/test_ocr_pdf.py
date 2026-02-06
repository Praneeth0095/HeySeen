"""
Test script for OCR_test.pdf - evaluate HeySeen's PDF loading capability
"""

from pathlib import Path
from heyseen.core.pdf_loader import PDFLoader, load_pdf
from rich.console import Console
from rich.table import Table
import time

console = Console()

def test_ocr_pdf():
    """Test loading OCR_test_1.pdf"""
    pdf_path = "pdf_examples/OCR_test_1.pdf"
    console.print(f"\n[bold cyan]Testing with: {pdf_path}[/bold cyan]\n")
    
    # Test 1: Metadata
    console.print("[yellow]→[/yellow] Loading PDF metadata...")
    with PDFLoader(pdf_path) as loader:
        metadata = loader.get_metadata()
        
        table = Table(title="PDF Metadata")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Title", metadata.title or "(none)")
        table.add_row("Author", metadata.author or "(none)")
        table.add_row("Page Count", str(metadata.page_count))
        table.add_row("File Size", f"{metadata.file_size / 1024:.1f} KB")
        
        console.print(table)
    
    # Test 2: Load pages at different DPIs
    console.print("\n[yellow]→[/yellow] Testing page loading at different DPIs...\n")
    
    dpi_tests = [150, 300]
    results = []
    
    for dpi in dpi_tests:
        start_time = time.time()
        pages = load_pdf(pdf_path, dpi=dpi, verbose=False)
        elapsed = time.time() - start_time
        
        results.append({
            "dpi": dpi,
            "pages": len(pages),
            "time": elapsed,
            "first_page_size": f"{pages[0].width}x{pages[0].height}",
            "memory_estimate": sum(p.width * p.height * 3 for p in pages) / (1024**2)  # MB (RGB)
        })
        
        console.print(f"  ✓ {dpi} DPI: {len(pages)} pages loaded in {elapsed:.2f}s")
    
    # Results table
    console.print()
    result_table = Table(title="Loading Performance")
    result_table.add_column("DPI", style="cyan")
    result_table.add_column("Pages", style="green")
    result_table.add_column("Time", style="yellow")
    result_table.add_column("First Page", style="magenta")
    result_table.add_column("Memory Est.", style="red")
    
    for r in results:
        result_table.add_row(
            str(r["dpi"]),
            str(r["pages"]),
            f"{r['time']:.2f}s",
            r["first_page_size"],
            f"{r['memory_estimate']:.1f} MB"
        )
    
    console.print(result_table)
    
    # Test 3: Save first page sample
    console.print("\n[yellow]→[/yellow] Saving first page sample to [cyan]examples/ocr_test_page0.png[/cyan]...")
    
    Path("examples").mkdir(exist_ok=True)
    pages_300dpi = load_pdf(pdf_path, dpi=300, verbose=False)
    pages_300dpi[0].image.save("examples/ocr_test_page0.png")
    
    console.print("  ✓ Saved successfully\n")
    
    # Summary
    console.print("[bold green]✅ All tests passed![/bold green]")
    console.print(f"[dim]Ready for Phase 1.2: Layout Detection[/dim]\n")

if __name__ == "__main__":
    test_ocr_pdf()
