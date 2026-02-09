#!/usr/bin/env python3
"""
Create HeySeen favicon with eye icon
"""
from PIL import Image, ImageDraw

def create_heyseen_favicon():
    """Create a 32x32 favicon with eye icon"""
    # Create image with transparent background
    size = 32
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # HeySeen brand color - yellow/orange
    color = (255, 184, 0, 255)  # #FFB800
    
    # Draw eye shape (ellipse)
    eye_box = [(4, 12), (28, 20)]
    draw.ellipse(eye_box, fill=color)
    
    # Draw pupil (circle in center)
    pupil_center = 16
    pupil_radius = 4
    pupil_box = [
        (pupil_center - pupil_radius, pupil_center - pupil_radius),
        (pupil_center + pupil_radius, pupil_center + pupil_radius)
    ]
    draw.ellipse(pupil_box, fill=(60, 60, 60, 255))
    
    # Draw highlight in pupil
    highlight_radius = 2
    highlight_box = [
        (pupil_center - highlight_radius - 1, pupil_center - highlight_radius - 1),
        (pupil_center + highlight_radius - 1, pupil_center + highlight_radius - 1)
    ]
    draw.ellipse(highlight_box, fill=(255, 255, 255, 200))
    
    # Save as ICO
    output_path = '/Users/m2pro/HeySeen/heyseen/server/static/favicon.ico'
    img.save(output_path, format='ICO', sizes=[(32, 32), (16, 16)])
    print(f"✓ Created HeySeen favicon at {output_path}")

if __name__ == '__main__':
    try:
        create_heyseen_favicon()
    except ImportError:
        print("PIL/Pillow not installed. Installing...")
        import subprocess
        subprocess.run(['pip', 'install', 'Pillow'], check=True)
        create_heyseen_favicon()
