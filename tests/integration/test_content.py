"""
Test content extraction with OCR_test.pdf
"""

from pathlib import Path
from heyseen.core.pdf_loader import load_pdf
from heyseen.core.layout_analyzer import LayoutAnalyzer
from heyseen.core.content_extractor import ContentExtractor
from rich.console import Console
from rich.table import Table
import time

console = Console()

def test_content_extraction():
    """Test content extraction on OCR_test_1.pdf"""

    pdf_path = "pdf_examples/OCR_test_1.pdf"
    console.print(f"\n[bold cyan]Phase 1.3: Content Extraction Test[/bold cyan]\n")
    
    # Load PDF
    console.print(f"[yellow]→[/yellow] Loading PDF...")
    pages = load_pdf(pdf_path, dpi=300, verbose=False)
    console.print(f"  ✓ Loaded {len(pages)} page(s)\n")
    
    # Detect layout
    console.print("[yellow]→[/yellow] Detecting layout...")
    analyzer = LayoutAnalyzer(device="mps", verbose=False)
    blocks = analyzer.detect_layout(pages[0].image, page_num=0)
    sorted_blocks = analyzer.sort_reading_order(blocks)
    console.print(f"  ✓ Detected {len(blocks)} blocks\n")
    
    # Extract content
    console.print("[yellow]→[/yellow] Initializing content extractor...")
    extractor = ContentExtractor(device="mps", use_math_ocr=False, verbose=True)
    console.print()
    
    console.print("[yellow]→[/yellow] Extracting content from blocks...")
    start_time = time.time()
    
    output_dir = Path("examples/extracted_content")
    contents = extractor.extract_page(
        pages[0].image,
        sorted_blocks,
        output_dir=output_dir,
    )
    
    elapsed = time.time() - start_time
    console.print(f"  ✓ Extracted {len(contents)} blocks in {elapsed:.2f}s\n")
    
    # Display results
    table = Table(title="Extracted Content (First 10 blocks)")
    table.add_column("#", style="cyan", width=3)
    table.add_column("Type", style="green", width=8)
    table.add_column("Content Preview", style="yellow", width=60)
    table.add_column("Status", style="magenta", width=10)
    
    for i, content in enumerate(contents[:10]):
        preview = ""
        status = ""
        
        if content.text:
            preview = content.text[:60] + "..." if len(content.text) > 60 else content.text
            status = "✓ Text"
        elif content.latex:
            preview = content.latex[:60]
            status = "✓ LaTeX"
        elif content.image_path:
            preview = Path(content.image_path).name
            status = "✓ Image"
        else:
            preview = "(empty)"
            status = "⚠ Empty"
        
        table.add_row(
            str(i),
            content.block_type,
            preview,
            status,
        )
    
    console.print(table)
    
    # Statistics
    console.print("\n[bold]Content Statistics:[/bold]")
    
    text_blocks = sum(1 for c in contents if c.text)
    latex_blocks = sum(1 for c in contents if c.latex)
    image_blocks = sum(1 for c in contents if c.image_path)
    empty_blocks = sum(1 for c in contents if not (c.text or c.latex or c.image_path))
    
    console.print(f"  Text blocks: {text_blocks}")
    console.print(f"  LaTeX blocks: {latex_blocks}")
    console.print(f"  Image blocks: {image_blocks}")
    console.print(f"  Empty blocks: {empty_blocks}")
    
    # Show sample extracted text
    console.print("\n[bold]Sample Extracted Text (first 3 blocks):[/bold]")
    for i, content in enumerate(contents[:3]):
        if content.text:
            console.print(f"\n[cyan]Block {i} ({content.block_type}):[/cyan]")
            console.print(f"  {content.text}")
    
    # Summary
    console.print("\n[bold green]✅ Phase 1.3 Test Complete![/bold green]")
    console.print(f"\n[dim]Performance: {len(contents)}/{elapsed:.2f}s = {len(contents)/elapsed:.1f} blocks/sec[/dim]")
    console.print(f"[dim]Extracted images saved to: {output_dir}[/dim]")
    console.print(f"[dim]Ready for Phase 1.4: TeX Reconstruction[/dim]\n")

if __name__ == "__main__":
    test_content_extraction()
