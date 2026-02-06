"""
Test layout detection with OCR_test.pdf
"""

from pathlib import Path
from heyseen.core.pdf_loader import load_pdf
from heyseen.core.layout_analyzer import LayoutAnalyzer
from rich.console import Console
from rich.table import Table
import time

console = Console()

def test_layout_detection():
    """Test Surya layout detection on OCR_test_1.pdf"""

    pdf_path = "pdf_examples/OCR_test_1.pdf"

    console.print(f"\n[bold cyan]Phase 1.2: Layout Detection Test[/bold cyan]\n")
    console.print(f"[yellow]→[/yellow] Loading PDF: {pdf_path}\n")
    
    # Load PDF
    pages = load_pdf(pdf_path, dpi=300, verbose=False)
    console.print(f"  ✓ Loaded {len(pages)} page(s)\n")
    
    # Initialize layout analyzer
    console.print("[yellow]→[/yellow] Initializing Surya layout detection model...")
    analyzer = LayoutAnalyzer(device="mps", verbose=True)
    console.print()
    
    # Detect layout
    console.print("[yellow]→[/yellow] Detecting layout blocks...")
    start_time = time.time()
    
    blocks = analyzer.detect_layout(pages[0].image, page_num=0)
    sorted_blocks = analyzer.sort_reading_order(blocks)
    
    elapsed = time.time() - start_time
    console.print(f"  ✓ Detected {len(blocks)} blocks in {elapsed:.2f}s\n")
    
    # Display results
    if blocks:
        table = Table(title="Detected Layout Blocks (Reading Order)")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("BBox (normalized)", style="yellow")
        table.add_column("Area", style="magenta")
        table.add_column("Conf", style="red")
        
        for block in sorted_blocks:
            bbox_str = f"[{block.bbox.x0:.2f}, {block.bbox.y0:.2f}, {block.bbox.x1:.2f}, {block.bbox.y1:.2f}]"
            table.add_row(
                str(block.block_id),
                block.block_type,
                bbox_str,
                f"{block.bbox.area:.3f}",
                f"{block.confidence:.2f}",
            )
        
        console.print(table)
    else:
        console.print("[red]⚠ No blocks detected![/red]")
    
    # Visualize
    console.print("\n[yellow]→[/yellow] Creating visualization...")
    
    Path("examples").mkdir(exist_ok=True)
    vis_image = analyzer.visualize_layout(pages[0].image, sorted_blocks)
    output_path = "examples/ocr_test_layout.png"
    vis_image.save(output_path)
    
    console.print(f"  ✓ Saved to: [cyan]{output_path}[/cyan]")
    
    # Summary
    console.print("\n[bold green]✅ Phase 1.2 Test Complete![/bold green]")
    
    block_types = {}
    for block in blocks:
        block_types[block.block_type] = block_types.get(block.block_type, 0) + 1
    
    console.print(f"\n[dim]Block type distribution:[/dim]")
    for btype, count in sorted(block_types.items()):
        console.print(f"  {btype}: {count}")
    
    console.print(f"\n[dim]Performance: {len(blocks)} blocks in {elapsed:.2f}s = {len(blocks)/elapsed:.1f} blocks/sec[/dim]")
    console.print(f"[dim]Ready for Phase 1.3: Content Extraction[/dim]\n")

if __name__ == "__main__":
    test_layout_detection()
