"""
Model Manager Module

Centralizes model loading to prevent duplication and memory waste.
Manages Surya Foundation models (shared) and Texify models.
"""

from typing import Optional, Dict, Any
import logging
from surya.foundation import FoundationPredictor
from surya.layout import LayoutPredictor
from surya.recognition import RecognitionPredictor
from surya.detection import DetectionPredictor

try:
    from texify.model.model import load_model as load_texify_model
    from texify.model.processor import load_processor as load_texify_processor
    TEXIFY_AVAILABLE = True
except ImportError:
    TEXIFY_AVAILABLE = False

try:
    from transformers import TableTransformerForObjectDetection, AutoImageProcessor
    TATR_AVAILABLE = True
except ImportError:
    TATR_AVAILABLE = False

logger = logging.getLogger(__name__)

class ModelManager:
    _instance = None
    
    def __init__(self, device: str = "mps"):
        self.device = device
        self._foundation = None
        self._layout = None
        self._detection = None
        self._recognition = None
        self._texify_model = None
        self._texify_processor = None
        self._table_model = None
        self._table_processor = None
        
    @classmethod
    def get_instance(cls, device: str = "mps"):
        if cls._instance is None:
            cls._instance = cls(device)
        return cls._instance

    def get_foundation_predictor(self) -> FoundationPredictor:
        if self._foundation is None:
            logger.info(f"Loading Foundation Model on {self.device}...")
            self._foundation = FoundationPredictor(device=self.device)
        return self._foundation

    def get_layout_predictor(self) -> LayoutPredictor:
        if self._layout is None:
            foundation = self.get_foundation_predictor()
            logger.info("Initializing Layout Predictor...")
            self._layout = LayoutPredictor(foundation)
        return self._layout

    def get_detection_predictor(self) -> DetectionPredictor:
        if self._detection is None:
            # DetectionPredictor loads its own model usually
            logger.info("Initializing Detection Predictor...")
            self._detection = DetectionPredictor()
        return self._detection

    def get_recognition_predictor(self) -> RecognitionPredictor:
        if self._recognition is None:
            foundation = self.get_foundation_predictor()
            # RecognitionPredictor needs DetectionPredictor for full OCR (auto-segmentation)
            # if we pass raw images/crops without boxes.
            detection = self.get_detection_predictor() # Ensure detection is loaded
            
            logger.info("Initializing Recognition Predictor...")
            try:
                self._recognition = RecognitionPredictor(
                    foundation_predictor=foundation,
                    detection_predictor=detection
                )
            except TypeError:
                # Fallback to positional or just foundation (older versions might differ)
                # But seeing the error "You need to pass in a detection predictor", 
                # implies we MUST pass it or we can't run on images.
                self._recognition = RecognitionPredictor(foundation)
        return self._recognition

    def get_texify_model(self):
        if not TEXIFY_AVAILABLE:
            return None, None
            
        if self._texify_model is None:
            logger.info(f"Loading Texify Model on {self.device}...")
            # We assume float16 for speed/memory on MPS
            import torch
            dtype = torch.float16 if self.device == "mps" else torch.float32
            
            self._texify_processor = load_texify_processor()
            self._texify_model = load_texify_model(
                checkpoint="vikp/texify", 
                device=self.device, 
                dtype=dtype
            )
        return self._texify_model, self._texify_processor

    def get_table_model(self):
        """Load Microsoft Table Transformer"""
        if not TATR_AVAILABLE:
            logger.warning("Transformers library not installed. Cannot load Table Transformer.")
            return None, None
            
        if self._table_model is None:
            logger.info(f"Loading Table Transformer on {self.device}...")
            try:
                self._table_processor = AutoImageProcessor.from_pretrained(
                    "microsoft/table-transformer-structure-recognition"
                )
                self._table_model = TableTransformerForObjectDetection.from_pretrained(
                    "microsoft/table-transformer-structure-recognition"
                ).to(self.device)
            except Exception as e:
                logger.error(f"Failed to load Table Transformer: {e}")
                return None, None
                
        return self._table_model, self._table_processor
