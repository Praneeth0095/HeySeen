"""
Visual test for OCR_test.pdf - create annotated version with page info
"""

from heyseen.core.pdf_loader import load_pdf
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_visual_test():
    """Create annotated image showing PDF page with metadata"""
    
    print("Loading OCR_test.pdf...")
    pages = load_pdf("pdf_examples/OCR_test.pdf", dpi=300, verbose=False)
    page = pages[0]
    
    # Create a copy to annotate
    img = page.image.copy()
    draw = ImageDraw.Draw(img)
    
    # Add border and info overlay
    width, height = img.size
    border_color = (255, 0, 0)  # Red
    border_width = 10
    
    # Draw border
    draw.rectangle(
        [(0, 0), (width-1, height-1)],
        outline=border_color,
        width=border_width
    )
    
    # Add text overlay (top-left corner)
    text_lines = [
        f"OCR Test PDF",
        f"Size: {width}x{height}px",
        f"DPI: {page.dpi}",
        f"Page: {page.page_num + 1}",
        "",
        "✓ PDF Loader Working!",
    ]
    
    # Background for text
    text_bg_height = 180
    draw.rectangle(
        [(0, 0), (500, text_bg_height)],
        fill=(0, 0, 0, 180)
    )
    
    # Draw text
    try:
        # Try to use a system font
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except:
        font = ImageFont.load_default()
    
    y_offset = 10
    for line in text_lines:
        draw.text((10, y_offset), line, fill=(255, 255, 255), font=font)
        y_offset += 30
    
    # Save annotated version
    output_path = "examples/ocr_test_annotated.png"
    img.save(output_path)
    print(f"✓ Saved annotated version to: {output_path}")
    print(f"  Original image size: {width}x{height}px")
    print(f"  File size: {Path(output_path).stat().st_size / 1024:.1f} KB")

if __name__ == "__main__":
    create_visual_test()
