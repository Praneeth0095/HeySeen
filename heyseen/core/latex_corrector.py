import os
import re
import requests
import logging
from typing import List
from pathlib import Path

logger = logging.getLogger(__name__)

class LatexCorrector:
    def __init__(self, llm_url: str, model: str = "qwen2.5-coder:7b", prompt_file: str = None):
        self.llm_url = llm_url
        self.model = model
        self.api_endpoint = f"{llm_url}/api/generate"
        
        # Load prompt template
        if prompt_file is None:
            prompt_file = Path(__file__).parent.parent / "prompts" / "latex_correction.txt"
        
        with open(prompt_file, 'r', encoding='utf-8') as f:
            self.prompt_template = f.read()

    def correct_file(self, input_path: str, output_path: str = None):
        """
        Reads a valid LaTeX file, splits it into chunks, corrects text via LLM,
        and writes back to output_path.
        """
        if not output_path:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_corrected{ext}"

        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split content into manageable chunks to avoid context window overflow
        # Using \newpage or \section as natural splitters is good, but simple character chunking
        # with overlap is safer to prevent splitting in the middle of a command.
        # Check strategy: Split by double newline (paragraphs) and group them.
        
        chunks = self._chunk_content(content)
        corrected_chunks = []
        
        total_chunks = len(chunks)
        print(f"Bắt đầu sửa lỗi {total_chunks} đoạn văn bản...")

        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{total_chunks}...")
            # Detect if chunk is mostly math or code, skip if needed? 
            # No, text might be interspersed.
            corrected = self._process_chunk(chunk)
            corrected_chunks.append(corrected)
            
            # Incremental save
            if (i + 1) % 5 == 0 or (i + 1) == total_chunks:
                temp_content = "\n\n".join(corrected_chunks + chunks[i+1:])
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(temp_content)
                print(f"  (Đã lưu tạm quá trình tại chunk {i+1})")

        full_content = "\n\n".join(corrected_chunks)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        print(f"Hoàn tất! File đã lưu tại: {output_path}")
        return output_path

    def _chunk_content(self, text: str, max_chars: int = 4000) -> List[str]:
        """
        Splits text into chunks roughly `max_chars` long, respecting paragraph boundaries.
        """
        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_len = 0

        for p in paragraphs:
            # If a single paragraph is huge, we force split it? 
            # For now assume paragraphs are reasonable.
            if current_len + len(p) > max_chars and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_len = 0
            
            current_chunk.append(p)
            current_len += len(p)
        
        if current_chunk:
            chunks.append("\n\n".join(current_chunk))
            
        return chunks

    def _process_chunk(self, text: str) -> str:
        """
        Sends LaTeX chunk to LLM for Vietnamese spell checking.
        """
        # Skip empty or very short chunks
        if len(text.strip()) < 10:
            return text

        prompt = self.prompt_template.format(text=text)
        
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1, # Low temperature for fidelity
                    "num_ctx": 8192 # Increase context window
                }
            }
            
            # Increased timeout for local LLM inference
            response = requests.post(self.api_endpoint, json=payload, timeout=300)
            response.raise_for_status()
            result = response.json()
            
            corrected_text = result.get('response', '').strip()
            
            # Remove <think>...</think> blocks common in DeepSeek-R1
            corrected_text = re.sub(r'<think>.*?</think>', '', corrected_text, flags=re.DOTALL).strip()
            
            # Post-processing to remove code blocks if LLM adds them
            # DeepSeek sometimes wraps output in ```latex ... ```
            match = re.search(r'```(?:latex)?\n(.*?)```', corrected_text, re.DOTALL)
            if match:
                corrected_text = match.group(1)
            
            # If no code block found, but text is substantial, accept it.
            # (Sometimes it just returns the text)
            
            # Simple sanity check: If length differs drastically (e.g. dropped content), fallback
            if len(corrected_text) < len(text) * 0.5: # Relaxed to 50%
                logger.warning("LLM output suspicious length (too short). Keeping original.")
                return text

            return corrected_text

        except Exception as e:
            logger.error(f"Error correcting chunk: {e}")
            return text
