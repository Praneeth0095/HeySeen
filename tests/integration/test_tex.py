"""
Integration Test: Phase 1.4 - TeX Reconstruction

Tests the complete pipeline: PDF → Layout → Content → TeX
"""

from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from heyseen.core.pdf_loader import load_pdf
from heyseen.core.layout_analyzer import LayoutAnalyzer
from heyseen.core.content_extractor import ContentExtractor
from heyseen.core.tex_builder import TeXBuilder

console = Console()


def test_tex_reconstruction():
    """Test complete PDF to TeX pipeline"""
    
    print("\n" + "="*80)
    print(" Phase 1.4: TeX Reconstruction Test")
    print("="*80 + "\n")

    # Configuration
    pdf_path = Path("pdf_examples/OCR_test_1.pdf")
    output_dir = Path("examples/tex_output")

    # Step 1: Load PDF
    print("→ Loading PDF...")
    pages = load_pdf(pdf_path, dpi=150)
    print(f"  ✓ Loaded {len(pages)} page(s)")
    
    # Step 2: Detect layout
    print("\n→ Detecting layout...")
    analyzer = LayoutAnalyzer(device="mps", verbose=False)
    
    all_blocks = []
    for page in pages:
        blocks = analyzer.detect_layout(page.image)
        all_blocks.append(blocks)
    
    total_blocks = sum(len(blocks) for blocks in all_blocks)
    print(f"  ✓ Detected {total_blocks} blocks across {len(pages)} page(s)")
    
    # Step 3: Extract content
    print("\n→ Extracting content...")
    extractor = ContentExtractor(device="mps", use_math_ocr=False, verbose=False)
    
    all_contents = []
    for page, blocks in zip(pages, all_blocks):
        contents = extractor.extract_page(page.image, blocks, output_dir=output_dir / "images")
        all_contents.append(contents)
    
    total_text = sum(sum(1 for c in contents if c.text) for contents in all_contents)
    total_images = sum(sum(1 for c in contents if c.image_path) for contents in all_contents)
    print(f"  ✓ Extracted {total_text} text blocks, {total_images} images")
    
    # Step 4: Build TeX document
    print("\n→ Building LaTeX document...")
    builder = TeXBuilder(output_dir=output_dir, verbose=True)
    
    document_info = {
        "title": "OCR Test Document",
        "author": "HeySeen Test Suite",
    }
    
    main_tex_path = builder.build_document(
        contents_per_page=all_contents,
        blocks_per_page=all_blocks,
        document_info=document_info,
    )
    
    # Step 5: Display results
    print("\n" + "="*80)
    print("✅ Phase 1.4 Test Complete!")
    print("="*80 + "\n")
    
    print("📁 Output Structure:")
    print(f"  {output_dir}/")
    print(f"  ├── main.tex")
    print(f"  ├── meta.json")
    print(f"  └── images/")
    
    if (output_dir / "images").exists():
        images = list((output_dir / "images").glob("*.png"))
        for img in images[:3]:
            print(f"      ├── {img.name}")
        if len(images) > 3:
            print(f"      └── ... ({len(images)-3} more)")
    
    print(f"\n📄 LaTeX file: {main_tex_path}")
    print(f"   Size: {main_tex_path.stat().st_size / 1024:.1f} KB")
    
    # Preview LaTeX content
    print("\n📋 LaTeX Preview (first 30 lines):")
    print("-" * 80)
    with open(main_tex_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        for i, line in enumerate(lines[:30], 1):
            print(f"{i:3d} | {line}", end="")
        if len(lines) > 30:
            print(f"... ({len(lines) - 30} more lines)")
    print("-" * 80)
    
    # Compilation instructions
    print("\n🔨 To compile the LaTeX document:")
    print(f"   cd {output_dir}")
    print(f"   pdflatex main.tex")
    print(f"   open main.pdf")
    
    print("\n✅ Ready for Phase 2: Quality & Robustness")


if __name__ == "__main__":
    test_tex_reconstruction()
