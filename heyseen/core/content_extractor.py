"""
Content Extractor Module

Extracts text, math, and images from layout blocks.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
from pathlib import Path
from PIL import Image
import re
import io
import logging

from surya.recognition import RecognitionPredictor, FoundationPredictor

try:
    from texify.inference import batch_inference
    from texify.model.model import load_model
    from texify.model.processor import load_processor
    TEXIFY_AVAILABLE = True
except ImportError:
    TEXIFY_AVAILABLE = False

from .layout_analyzer import LayoutBlock, BlockType
from .table_recognizer import TableRecognizer


# Setup logger
logger = logging.getLogger(__name__)


@dataclass
class ExtractedContent:
    """Content extracted from a layout block"""
    
    block_id: int
    block_type: BlockType
    text: Optional[str] = None
    latex: Optional[str] = None
    image_path: Optional[str] = None
    confidence: float = 0.0
    
    def __repr__(self) -> str:
        preview = ""
        if self.text:
            preview = self.text[:50] + "..." if len(self.text) > 50 else self.text
        elif self.latex:
            preview = self.latex[:50] + "..." if len(self.latex) > 50 else self.latex
        elif self.image_path:
            preview = Path(self.image_path).name
        return f"Content({self.block_type}, {preview!r})"


from .model_manager import ModelManager
from .llm_processor import LLMProcessor

class ContentExtractor:
    """
    Extracts content from layout blocks using OCR.
    """
    
    def __init__(
        self,
        device: str = "mps",
        use_math_ocr: bool = True,
        verbose: bool = True,
        manager: Optional[ModelManager] = None,
        llm_url: Optional[str] = None
    ) -> None:
        """
        Initialize content extractor.
        """
        self.device = device
        self.use_math_ocr = use_math_ocr
        self.verbose = verbose
        
        if manager is None:
             manager = ModelManager.get_instance(device)
        
        logger.info(f"Loading OCR models on {device}...")
        
        # Load Surya recognition model via Manager
        self.text_recognizer = manager.get_recognition_predictor()
        
        # Load LLM Processor if URL provided
        self.llm_processor = None
        if llm_url:
            self.llm_processor = LLMProcessor(api_url=llm_url)
            logger.info(f"✓ LLM Post-processing enabled: {llm_url}")
        
        # Load Math Recognizer via Manager
        self.math_recognizer = False
        if use_math_ocr and TEXIFY_AVAILABLE:
            logger.info("Loading Texify math OCR model...")
            try:
                self.math_model, self.math_processor = manager.get_texify_model()
                self.math_recognizer = True
                logger.info("✓ Texify loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load Texify: {e}")
                self.math_model = None
        
        # Load Table Recognizer
        self.table_recognizer = None
        try:
            self.table_recognizer = TableRecognizer(device=device, manager=manager)
            if self.table_recognizer.model:
                 logger.info("✓ Table Transformer loaded successfully")
            else:
                 logger.warning("Table Transformer model unavailable (check libs)")
        except Exception as e:
            logger.warning(f"Failed to init Table Transformer: {e}")
                
        logger.info("✓ OCR models loaded")

    
    def extract_block(
        self,
        image: Image.Image,
        block: LayoutBlock,
        output_dir: Optional[Path] = None,
    ) -> ExtractedContent:
        """
        Extract content from a single block.
        
        Args:
            image: Full page image
            block: Layout block to extract
            output_dir: Directory to save extracted images
            
        Returns:
            ExtractedContent object
        """
        # Crop block region
        x0, y0, x1, y1 = block.bbox.to_pixels(image.width, image.height)
        block_image = image.crop((x0, y0, x1, y1))
        
        # Initialize content object
        content = ExtractedContent(
            block_id=block.block_id,
            block_type=block.block_type,
            confidence=block.confidence,
        )
        
        # Route to appropriate extractor
        if block.block_type in ["text", "title", "caption", "section", "subsection", "list-item"]:
            # Pass bbox in pixel coordinates for recognition
            bbox = [x0, y0, x1, y1]
            content.text = self._extract_text(image, bbox)
        elif block.block_type == "math":
            if self.use_math_ocr and self.math_recognizer:
                content.latex = self._extract_math(block_image)
            else:
                # Fallback: save as image
                content.image_path = self._save_image(block_image, block, output_dir)
        elif block.block_type == "table":
             # Try TATR first
             if self.table_recognizer and self.table_recognizer.model:
                 try:
                     print(f"DEBUG: Processing Table Block {block.block_id}")
                     content.latex = self.table_recognizer.process_table(
                         block_image, 
                         ocr_callback=self._ocr_cell_callback
                     )
                     # Fallback if TATR returns empty result
                     if not content.latex:
                         # Fallback to Text extraction for the whole block
                         text = self._extract_text(block_image, [0, 0, block_image.width, block_image.height])
                         content.text = text
                         # IMPORTANT: If text fallback is used, we must ensure TexBuilder sees it.
                         # TexBuilder checks content.latex for tables. If empty, it looks for content.text via our new patch 
                         # OR we can change the block type to "paragraph" or "text" here?
                         # Changing type is safer for merging logic in TexBuilder.
                         # But block_type is passed from layout, usually immutable in ExtractedContent?
                         # Let's try forcing it.
                         content.block_type = "text" # Force it to act like text
                         
                 except Exception as e:
                     logger.warning(f"Table recognition failed: {e}. Falling back to image.")
                     content.image_path = self._save_image(block_image, block, output_dir)
             else:
                 content.image_path = self._save_image(block_image, block, output_dir)
        elif block.block_type == "figure":
            content.image_path = self._save_image(block_image, block, output_dir)
        
        return content
    
    def _ocr_cell_callback(self, cell_image: Image.Image) -> str:
        """Helper for TableRecognizer to OCR individual cells"""
        w, h = cell_image.size
        if w == 0 or h == 0: return ""
        
        # 1. Try Text Extraction
        text = self._extract_text(cell_image, [0, 0, w, h])
        
        # 2. Clean up tags
        import re
        # Remove <math> tags but keep content if it's not structural noise
        # Actually <math> tags often wrap latex content we WANT. 
        # e.g. <math>\alpha</math> -> \alpha
        text = re.sub(r'<math[^>]*>', '', text)
        text = re.sub(r'</math>', '', text)
        
        return text.strip()

    def _extract_text(self, image: Image.Image, bbox: List[int]) -> str:
        """Extract text using Surya recognition"""
        try:
            # Run Surya recognition with bbox from layout detection
            # bbox format: [x0, y0, x2, y2] in pixel coordinates
            
            # Note: Surya expects full image + bbox, OR crop + bbox=[0,0,w,h].
            # When calling from table recognizer, image is a crop.
            
            results = self.text_recognizer(
                images=[image],
                bboxes=[[bbox]],  # List of bbox lists per image
                task_names=["ocr_with_boxes"]  # Supported task name
            )
            if results and len(results) > 0:
                # Concatenate all text lines
                text_lines = [line.text for line in results[0].text_lines]
                return " ".join(text_lines).strip()
            return ""
        except Exception as e:
            logger.warning(f"Text extraction failed for block: {e}")
            return ""
    
    def _extract_math(self, image: Image.Image) -> str:
        """Extract math as LaTeX using Texify"""
        if not self.math_recognizer:
            return ""
        
        try:
            # Convert PIL Image to format Texify expects
            from texify.inference import batch_inference
            
            # Run Texify inference
            results = batch_inference(
                images=[image],
                model=self.math_model,
                processor=self.math_processor,
            )
            
            if results and len(results) > 0:
                latex = results[0].strip()
                # Clean up Texify output
                latex = self._clean_texify_output(latex)
                
                # --- Math Hallucination Guard (Phase 2.5) ---
                # Fallback to text if Texify produces Vietnamese text instead of math
                if self._has_vietnamese_chars(latex, threshold=0.3):
                     logger.info(f"Math Hallucination detected (~{len(latex)} chars). Fallback to Text.")
                     # Fallback to Text OCR for this block
                     # We reuse internal recognition since we have the image crop
                     # But _extract_text expects full image + bbox
                     # So we must perform OCR on this cropped image directly?
                     # Surya input: Image or [Image]
                     # self.text_recognizer expects {images, languages}
                     
                     # Simple workaround: Return invalid math marker so caller handles?
                     # Or run text extraction now.
                     try:
                         ocr_res = self.text_recognizer(images=[image], languages=["vi"])
                         if ocr_res and len(ocr_res) > 0:
                             fallback_text = " ".join([l.text for l in ocr_res[0].text_lines])
                             return f"\\text{{{fallback_text}}}"
                     except:
                         pass

                return latex
            return ""
        except Exception as e:
            logger.warning(f"Math extraction failed: {e}")
            return ""
    
    def _has_vietnamese_chars(self, text: str, threshold: float = 0.10) -> bool:
        """
        Detect if text contains Vietnamese diacritics (Force_Text marker).
        
        Args:
            text: Input text
            threshold: Minimum ratio of Vietnamese chars to total chars (default 10%)
            
        Returns:
            True if Vietnamese char ratio exceeds threshold
        """
        if not text or len(text) < 5:
            return False
        
        # Vietnamese diacritics (combining and precomposed)
        vietnamese_chars = 'áàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴĐ'
        
        viet_count = sum(1 for c in text if c in vietnamese_chars)
        total_alpha = sum(1 for c in text if c.isalpha())
        
        if total_alpha == 0:
            return False
        
        ratio = viet_count / total_alpha
        return ratio > threshold
    
    def _calculate_math_density(self, text: str) -> float:
        """
        Calculate density of mathematical symbols and LaTeX keywords.
        
        Returns:
            Score from 0.0 to 1.0 (higher = more likely to be math)
        """
        if not text or len(text) < 3:
            return 0.0
        
        import re
        
        # Math operators and symbols
        math_chars = r'[+\-*/=<>≤≥≠∈∉⊂⊃∪∩∀∃⇒⇔→←∑∏∫±×÷√∞∂∇]'
        math_count = len(re.findall(math_chars, text))
        
        # LaTeX commands (backslash followed by letters)
        latex_commands = len(re.findall(r'\\[a-zA-Z]+', text))
        
        # LaTeX symbols
        latex_symbols = len(re.findall(r'[{}$^_]', text))
        
        # Calculate weighted score
        total_score = (math_count * 2) + (latex_commands * 3) + (latex_symbols * 1)
        
        # Normalize by text length
        density = total_score / len(text)
        
        # Cap at 1.0
        return min(density, 1.0)
    
    def _looks_like_math_block(self, block: LayoutBlock, text: str) -> bool:
        """
        Visual + textual heuristics to detect math blocks.
        
        Enhanced Criteria:
        1. Small-medium area (< 0.25 of page)
        2. Short text (< 300 chars) - likely isolated formula
        3. Contains math patterns OR is small & isolated
        4. Vietnamese charset filter: Force bypass if > 10% Vietnamese chars
        5. Math density check: Require minimum math symbol density
        """
        # FORCE_TEXT: If contains significant Vietnamese, bypass Texify
        if self._has_vietnamese_chars(text):
            return False
        # Calculate math density
        math_density = self._calculate_math_density(text)
        
        # Require minimum math density to consider as math
        if math_density < 0.05:  # Less than 5% math symbols
            return False
        
        # Size heuristic: medium blocks could be formulas
        area = block.bbox.area
        if area > 0.25:  # Too large (more than 1/4 page)
            return False
        
        width = block.bbox.x1 - block.bbox.x0
        height = block.bbox.y1 - block.bbox.y0
        aspect_ratio = width / height if height > 0 else 1.0
        
        # Text length: short blocks are candidates
        text_len = len(text) if text else 0
        word_count = len(text.split()) if text else 0
        
        # Very short blocks with math patterns
        if text_len < 300:
            if self._contains_display_math(text) or math_density > 0.15:
                return True
            # Small isolated blocks (likely formulas)
            if area < 0.12 and aspect_ratio < 6.0 and word_count < 40 and math_density > 0.10:
                return True
        
        return False
    
    def _contains_display_math(self, text: str) -> bool:
        """
        Detect if text likely contains display math expressions.
        
        Heuristics:
        - High density of math symbols (∀∃∫∑∏√±≤≥≠≈∞)
        - LaTeX commands (\\int, \\sum, \\frac, etc.)
        - Block characteristics (small, centered)
        
        Note: Since Surya doesn't recognize Unicode math symbols well,
        this will primarily detect already-LaTeX-formatted math.
        For raw symbols, we'll need visual detection.
        """
        import re
        
        if not text or len(text) < 5:
            return False
        
        # Check for common LaTeX math patterns
        latex_patterns = [
            r'\\frac\{',  # Fractions
            r'\\int',  # Integrals
            r'\\sum',  # Summations
            r'\\prod',  # Products
            r'\\lim',  # Limits
            r'\\sqrt',  # Square roots
            r'\\partial',  # Partial derivatives
            r'\\infty',  # Infinity
            r'\\forall', # Forall
            r'\\exists', # Exists
            r'\\begin\{(?:equation|align|gather|multline)',  # Math environments
            r'\$\$',  # Display math delimiters
        ]
        
        for pattern in latex_patterns:
            if re.search(pattern, text):
                return True
        
        # Check for high density of mathematical operators
        # Expanded to include logic and more symbols
        math_chars = r'[+\-*/=<>≤≥≠∈∉⊂⊃∪∩∀∃⇒⇔→←∑∏∫]'
        operator_count = len(re.findall(math_chars, text))
        if operator_count > len(text) * 0.1:  # More than 10% operators
            return True
        
        return False
    
    def _extract_display_math_with_texify(
        self,
        text: str,
        image: Image.Image,
        block: LayoutBlock,
        output_dir: Optional[Path],
    ) -> tuple:
        """
        Extract display math blocks from text using Texify.
        
        Strategy: Crop the entire text block and run Texify on it
        (simpler approach without trying to parse positions).
        
        Returns:
            (cleaned_text, list_of_math_contents)
        """
        import re
        
        math_contents = []
        
        if not self.math_recognizer:
            return text, math_contents
        
        try:
            # Crop the entire block
            x0, y0, x1, y1 = block.bbox.to_pixels(image.width, image.height)
            math_image = image.crop((x0, y0, x1, y1))
            
            # Save debug image (optional)
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                debug_path = output_dir / f"math_block_{block.block_id}.png"
                math_image.save(debug_path)
            
            # Run Texify
            from texify.inference import batch_inference
            results = batch_inference(
                images=[math_image],
                model=self.math_model,
                processor=self.math_processor
            )
            
            if results and len(results) > 0:
                latex = self._clean_texify_output(results[0])
                
                # Only create math block if latex is not empty (not filtered)
                if latex:
                    logger.debug(f"✓ Texify extracted: {latex[:60]}...")
                    
                    # Create math content
                    math_content = ExtractedContent(
                        block_id=block.block_id * 1000,  # Unique ID
                        block_type="math",
                        confidence=block.confidence,
                    )
                    math_content.latex = latex
                    math_contents.append(math_content)
                    
                    # Return empty text (content moved to math block)
                    return "", math_contents
                else:
                    # Filtered as hallucination, keep original text
                    return text, math_contents
        
        except Exception as e:
            # On error, return original text
            logger.warning(f"Texify failed on block {block.block_id}: {e}")
            pass
        
        return text, math_contents
    
    def _clean_texify_output(self, latex: str, min_confidence: float = 0.3) -> str:
        """
        Clean Texify output and filter hallucinations.
        
        Args:
            latex: Raw LaTeX output from Texify
            min_confidence: Minimum confidence score (default 0.3)
            
        Returns:
            Cleaned LaTeX or empty string if filtered
        """
        import re
        
        # Remove extra whitespace
        latex = re.sub(r'\s+', ' ', latex).strip()
        
        # Calculate confidence score based on LaTeX validity
        confidence = self._calculate_latex_confidence(latex)
        if confidence < min_confidence:
            logger.debug(f"Filtered low-confidence Texify output (score={confidence:.2f}): {latex[:60]}")
            return ""
        
        # Specific Vietnamese corrections for common Texify errors
        # Texify usually fails to render Vietnamese in math, turning "với" into "v'oi"
        if r"v'oi" in latex:
             latex = latex.replace(r"v'oi", r"với")
        if r"h.t.d." in latex:
             latex = latex.replace(r"h.t.d.", r"h.t.đ")
    
    def _calculate_latex_confidence(self, latex: str) -> float:
        """
        Calculate confidence score for LaTeX output.
        
        Returns:
            Score from 0.0 to 1.0 (higher = more confident)
        """
        import re
        
        if not latex or len(latex) < 3:
            return 0.0
        
        score = 0.5  # Base score
        
        # Positive signals
        has_math_env = bool(re.search(r'\\(frac|int|sum|prod|sqrt|lim)', latex))
        has_greek = bool(re.search(r'\\(alpha|beta|gamma|delta|epsilon|theta|lambda|mu|sigma|pi|omega)', latex))
        has_operators = bool(re.search(r'[+\-*/=<>≤≥∫∑∏]', latex))
        has_brackets = bool(re.search(r'[\[\]\{\}()]', latex))
        
        if has_math_env:
            score += 0.2
        if has_greek:
            score += 0.15
        if has_operators:
            score += 0.1
        if has_brackets:
            score += 0.05
        
        # Negative signals (text-like patterns)
        has_long_words = any(len(word) > 15 for word in latex.split())
        has_spaces_ratio = latex.count(' ') / len(latex) if len(latex) > 0 else 0
        
        if has_long_words:
            score -= 0.2
        if has_spaces_ratio > 0.15:  # More than 15% spaces
            score -= 0.15
        
        return max(0.0, min(1.0, score))

        # Remove outer $$ delimiters (tex_builder will add \[...\])
        if latex.startswith('$$') and latex.endswith('$$'):
            latex = latex[2:-2].strip()
        elif latex.startswith('$') and latex.endswith('$') and not latex[1:-1].count('$'):
            latex = latex[1:-1].strip()
        
        # Filter hallucinations: Check for text-like patterns
        # Common hallucination patterns from Vietnamese text
        text_patterns = [
            r'^#\s',  # Starts with #
            r'trong\s+(d[óo]|đó|d\\hat\{o\})',  # "trong đó", "trong do", "trong d\hat{o}"
            r'\\mathrm\{Trong', # Target Texify output "\mathrm{Trong..."
            r'Trong~d', # Target "Trong~d..."
            r'bu[ôo]c\s+\d',  # "Bước 1", "Bước 2"
            r'h[ệe]\s+s[ốo]',  # "hệ số"
            r'd[uưứừửữự][oơớờởỡợ]c\s+tính',  # "được tính", "duợc tính"
            r'ki[ểe]m\s+tra',  # "kiểm tra"
            r'\*\*.*\*\*',  # Markdown bold **text**
        ]
        
        # Check if this looks like Vietnamese text rather than math
        is_text = any(re.search(pattern, latex, re.IGNORECASE) for pattern in text_patterns)
        
        if is_text:
            logger.debug(f"Filtered text hallucination: {latex[:60]}")
            return ""  # Skip this block
        
        return latex
    
    def _save_image(
        self,
        image: Image.Image,
        block: LayoutBlock,
        output_dir: Optional[Path],
    ) -> Optional[str]:
        """Save extracted image to file"""
        if output_dir is None:
            return None
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"page_{block.page_num:03d}_{block.block_type}_{block.block_id:02d}.png"
        filepath = output_dir / filename
        
        image.save(filepath)
        return str(filepath)
    
    def extract_page(
        self,
        image: Image.Image,
        blocks: List[LayoutBlock],
        output_dir: Optional[Path] = None,
    ) -> List[ExtractedContent]:
        """
        Extract content from all blocks in a page.
        
        Args:
            image: Full page image
            blocks: List of layout blocks
            output_dir: Directory to save extracted images
            
        Returns:
            List of ExtractedContent objects
        """
        contents = []
        
        # Separate blocks by type for batch processing
        text_blocks = []
        text_indices = []
        for i, block in enumerate(blocks):
            if block.block_type in ["text", "title", "caption"]:
                text_blocks.append(block)
                text_indices.append(i)
        
        # Batch extract text blocks
        text_results = {}
        if text_blocks:
            # Crop images for each text block to ensure 1:1 mapping and correct recognition
            text_crops = []
            for b in text_blocks:
                x0, y0, x1, y1 = b.bbox.to_pixels(image.width, image.height)
                # Ensure valid crop (handle edge cases)
                x0, y0 = max(0, x0), max(0, y0)
                x1, y1 = min(image.width, x1), min(image.height, y1)
                if x1 > x0 and y1 > y0:
                    text_crops.append(image.crop((x0, y0, x1, y1)))
                else:
                    text_crops.append(image) # Placeholder for invalid box (very rare)
            
            try:
                # Text recognition on crops with explicit bboxes (whole crop)
                # This bypasses the need for an internal detector
                pixel_bboxes = [
                    [[0, 0, crop.width, crop.height]] for crop in text_crops
                ]
                
                ocr_results = self.text_recognizer(
                    images=text_crops,
                    bboxes=pixel_bboxes
                )
                
                if ocr_results:
                    for block, result in zip(text_blocks, ocr_results):
                        # Combine lines if multiple found in one crop (unlikely for line blocks)
                        text = " ".join([l.text for l in result.text_lines]).strip()
                        text_results[block.block_id] = text
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Batch text extraction failed: {e}")
        
        # --- Batch Math Extraction Strategy ---
        math_tasks = [] # (index_in_contents, crop_image, block_id)
        contents = [None] * len(blocks) # Placeholder list
        
        for i, block in enumerate(blocks):
            content = ExtractedContent(
                block_id=block.block_id,
                block_type=block.block_type,
                confidence=block.confidence,
            )
            contents[i] = content
            
            x0, y0, x1, y1 = block.bbox.to_pixels(image.width, image.height)
            
            if block.block_type == "math":
                if self.use_math_ocr and self.math_recognizer:
                    block_image = image.crop((x0, y0, x1, y1))
                    math_tasks.append((i, block_image, block.block_id, "math_block"))
                else:
                    block_image = image.crop((x0, y0, x1, y1))
                    content.image_path = self._save_image(block_image, block, output_dir)
            
            elif block.block_type in ["text", "title", "caption"]:
                text = text_results.get(block.block_id, "")
                content.text = text
                
                # Check for math inside text block
                if self.math_recognizer and self._contains_display_math(text):
                     # Queue for re-check with Texify
                     # We crop the WHOLE block as per current strategy
                     block_image = image.crop((x0, y0, x1, y1))
                     math_tasks.append((i, block_image, block.block_id, "text_math"))
                     
            elif block.block_type == "table":
                 block_image = image.crop((x0, y0, x1, y1))
                 
                 # Try TATR if available
                 if self.table_recognizer and self.table_recognizer.model:
                     try:
                         # print(f"DEBUG: Processing Table Block {block.block_id}")
                         content.latex = self.table_recognizer.process_table(
                             block_image, 
                             ocr_callback=self._ocr_cell_callback
                         )
                         if not content.latex:
                             content.image_path = self._save_image(block_image, block, output_dir)
                     except Exception as e:
                         # logger.warning(f"Table recognition failed for {block.block_id}: {e}")
                         content.image_path = self._save_image(block_image, block, output_dir)
                 else:
                     content.image_path = self._save_image(block_image, block, output_dir)

            elif block.block_type == "figure":
                block_image = image.crop((x0, y0, x1, y1))
                content.image_path = self._save_image(block_image, block, output_dir)

        # Run Batch Texify
        if math_tasks:
            from texify.inference import batch_inference
            
            # Prepare images
            math_images = [task[1] for task in math_tasks]
            
            if self.verbose:
                 print(f"  Running Texify on {len(math_images)} detected math regions...")
            
            try:
                results = batch_inference(
                    images=math_images,
                    model=self.math_model,
                    processor=self.math_processor
                )
                
                # Map results back
                for (idx, _, block_id, task_type), latex in zip(math_tasks, results):
                    clean_latex = self._clean_texify_output(latex)
                    
                    if not clean_latex:
                        continue # Skip filtered/empty results
                        
                    content = contents[idx]
                    
                    if task_type == "math_block":
                         content.latex = clean_latex
                         content.text = None # Clear any text garbage
                    elif task_type == "text_math":
                         # Replace text content with math
                         content.latex = clean_latex
                         content.text = None
                         # Create a sub-content if we wanted to preserve structure, 
                         # but current schema is 1 block = 1 content type.
                         # Changing type effectively
                         content.block_type = "math" 
                         
            except Exception as e:
                logger.warning(f"Batch Texify failed: {e}")

        # Post-process Text with LLM (if enabled)
        if self.llm_processor:
             for content in contents:
                 if content.text and len(content.text) > 20: # Skip very short snippets
                     if self.verbose: 
                        print(f"  Fixing text block {content.block_id} with LLM...", end="\r")
                     content.text = self.llm_processor.correct_text(content.text)
             
             if self.verbose: print(f"  ✓ LLM Post-processing complete.           ")

        # Post-process: Link equation numbers to math blocks
        from .equation_linker import link_equation_numbers_to_math
        
        # Convert blocks to have text attribute for linking
        for i, block in enumerate(blocks):
            if i < len(contents):
                setattr(block, 'text', contents[i].text)
        
        eq_links = link_equation_numbers_to_math(blocks)
        
        # Merge equation numbers into math blocks
        for math_id, eq_num_id in eq_links:
            # Find corresponding content objects
            math_content = next((c for c in contents if c.block_id == math_id), None)
            eq_num_content = next((c for c in contents if c.block_id == eq_num_id), None)
            
            if math_content and eq_num_content and eq_num_content.text:
                # Append equation number to LaTeX
                if math_content.latex:
                    # Add \tag{} for equation number
                    import re
                    eq_num = eq_num_content.text.strip()
                    # Extract number from parentheses
                    match = re.search(r'\((.+?)\)', eq_num)
                    if match:
                        num = match.group(1)
                        math_content.latex += f" \\tag{{{num}}}"
                
                # Remove equation number from contents list
                contents = [c for c in contents if c.block_id != eq_num_id]
        
        return contents
    
    def batch_extract(
        self,
        images: List[Image.Image],
        blocks_per_page: List[List[LayoutBlock]],
        output_dir: Optional[Path] = None,
    ) -> List[List[ExtractedContent]]:
        """
        Extract content from multiple pages.
        
        Args:
            images: List of page images
            blocks_per_page: List of block lists (one per page)
            output_dir: Directory to save extracted images
            
        Returns:
            List of content lists (one per page)
        """
        all_contents = []
        
        for page_num, (image, blocks) in enumerate(zip(images, blocks_per_page)):
            if self.verbose:
                print(f"  Extracting page {page_num + 1}/{len(images)}...")
            
            contents = self.extract_page(image, blocks, output_dir)
            all_contents.append(contents)
        
        return all_contents


def extract_content(
    image: Image.Image,
    blocks: List[LayoutBlock],
    device: str = "mps",
    output_dir: Optional[Path] = None,
    verbose: bool = False,
) -> List[ExtractedContent]:
    """
    Convenience function to extract content from a single page.
    
    Args:
        image: Page image
        blocks: Detected layout blocks
        device: Device to run on
        output_dir: Directory to save images
        verbose: Print messages
        
    Returns:
        List of extracted contents
    """
    extractor = ContentExtractor(device=device, verbose=verbose)
    return extractor.extract_page(image, blocks, output_dir)
