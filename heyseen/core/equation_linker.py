"""
Equation Number Detection and Linking Module

Detects equation numbers like (1), (2.1), (3a) and links them to nearby math blocks.
"""

import re
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class EquationNumber:
    """Detected equation number"""
    text: str  # e.g., "(1)", "(2.1)"
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1) in normalized coords
    block_id: int
    

def detect_equation_numbers(text: str) -> List[str]:
    """
    Detect equation number patterns in text.
    
    Patterns:
    - (1), (2), ..., (99)
    - (1.1), (2.3), (A.1)
    - (1a), (2b)
    
    Args:
        text: Input text
        
    Returns:
        List of detected equation numbers
    """
    patterns = [
        r'\(\d+\)',           # (1), (10)
        r'\(\d+\.\d+\)',      # (1.1), (2.3)
        r'\([A-Z]\.\d+\)',    # (A.1), (B.2)
        r'\(\d+[a-z]\)',      # (1a), (2b)
    ]
    
    numbers = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        numbers.extend(matches)
    
    return numbers


def is_equation_number_block(text: str, bbox_area: float) -> bool:
    """
    Check if a text block is likely an equation number.
    
    Criteria:
    1. Contains only equation number pattern
    2. Very small area (< 2% of page)
    3. Located on the right side of page (x > 0.7)
    
    Args:
        text: Block text
        bbox_area: Normalized area (0-1)
        
    Returns:
        True if likely equation number
    """
    if not text:
        return False
    
    # Must be very small
    if bbox_area > 0.02:
        return False
    
    # Check pattern
    text = text.strip()
    numbers = detect_equation_numbers(text)
    
    # Should match entire text (no extra content)
    if numbers and len(numbers) == 1:
        # Allow some whitespace
        if text.replace(' ', '') == numbers[0].replace(' ', ''):
            return True
    
    return False


def link_equation_numbers_to_math(
    all_blocks: List,
    page_width: float = 1.0,
    proximity_threshold: float = 0.10
) -> List[Tuple[int, int]]:
    """
    Link equation number blocks to nearby math blocks.
    
    Strategy (Bbox Proximity):
    - Equation numbers are typically right-aligned (x > 0.7)
    - Math blocks are centered or left-aligned
    - If y-coordinates align (±5%) and horizontal distance < 10% page width, link them
    
    Args:
        all_blocks: List of layout blocks with bbox attributes
        page_width: Normalized page width (default 1.0)
        proximity_threshold: Maximum horizontal distance (default 10%)
        
    Returns:
        List of (math_block_id, eq_num_block_id) pairs
    """
    links = []
    
    # Separate equation numbers and math blocks
    eq_num_blocks = []
    math_blocks = []
    
    for block in all_blocks:
        if hasattr(block, 'block_type') and hasattr(block, 'bbox'):
            if block.block_type == "text":
                # Check if it's an equation number
                text = getattr(block, 'text', '')
                if is_equation_number_block(text, block.bbox.area):
                    eq_num_blocks.append(block)
            elif block.block_type == "math":
                math_blocks.append(block)
    
    # Match equation numbers to math blocks
    for eq_block in eq_num_blocks:
        eq_x = (eq_block.bbox.x0 + eq_block.bbox.x1) / 2
        eq_y = (eq_block.bbox.y0 + eq_block.bbox.y1) / 2
        
        # Find closest math block with aligned y-coordinate
        best_match = None
        best_distance = float('inf')
        
        for math_block in math_blocks:
            math_x = (math_block.bbox.x0 + math_block.bbox.x1) / 2
            math_y = (math_block.bbox.y0 + math_block.bbox.y1) / 2
            
            # Check vertical alignment (y-coordinate within ±5%)
            if abs(math_y - eq_y) > 0.05:
                continue
            
            # Check horizontal proximity
            h_distance = abs(math_x - eq_x)
            if h_distance < proximity_threshold and h_distance < best_distance:
                best_match = math_block
                best_distance = h_distance
        
        if best_match:
            links.append((best_match.block_id, eq_block.block_id))
    
    return links
