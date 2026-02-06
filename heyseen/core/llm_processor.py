"""
LLM Processor Module

Handles communication with Local LLM (Ollama) for OCR correction.
"""

import requests
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class LLMProcessor:
    def __init__(self, api_url: str = "http://192.168.1.100:11434", model: str = "deepseek-r1:8b"):
        self.api_url = api_url
        self.model = model
        self.timeout = 30 # seconds

    def correct_text(self, text: str, context: str = "") -> str:
        """
        Send text to LLM for OCR correction.
        
        Args:
            text: Raw OCR text (with errors like 'Nhửn diửn')
            context: Optional context (e.g. previous/next sentence)
            
        Returns:
            Corrected text
        """
        if not text or len(text) < 5:
            return text
            
        prompt = f"""You are a Vietnamese OCR proofreader. Fix spelling errors in the following text, especially math/technical terms. 
        Keep LaTeX formulas (start with $, \\, or inside $$) EXACTLY as is.
        Only output the corrected text. Do not add explanations.
        
        Input: {text}
        Output:"""

        try:
            response = requests.post(
                f"{self.api_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1 # Low temp for factual correction
                    }
                },
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                corrected = result.get("response", "").strip()
                # strip <think> tag from deepseek-r1
                if "<think>" in corrected:
                    corrected = corrected.split("</think>")[-1].strip()
                
                # Basic sanity check: if length changes drastically, discard
                if len(corrected) < len(text) * 0.5 or len(corrected) > len(text) * 1.5:
                     logger.warning(f"LLM output suspicious length. Keeping original.")
                     return text
                     
                return corrected
            else:
                logger.warning(f"LLM Request failed: {response.status_code}")
                return text
                
        except Exception as e:
            logger.warning(f"LLM Connection failed: {e}")
            return text
