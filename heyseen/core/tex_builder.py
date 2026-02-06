"""
TeX Builder Module

Reconstructs LaTeX documents from extracted content.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path
import json
from datetime import datetime

from .content_extractor import ExtractedContent
from .layout_analyzer import LayoutBlock


@dataclass
class TeXDocument:
    """LaTeX document metadata and content"""
    
    title: str = "Converted Document"
    author: str = "HeySeen"
    date: str = ""
    pages: List[Dict] = None
    
    def __post_init__(self):
        if not self.date:
            self.date = datetime.now().strftime("%Y-%m-%d")
        if self.pages is None:
            self.pages = []


class TeXBuilder:
    """Build LaTeX documents from extracted content"""
    
    def __init__(self, output_dir: Path, verbose: bool = True):
        """
        Initialize TeX builder.
        
        Args:
            output_dir: Directory to save output files
            verbose: Print progress messages
        """
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        
        # Create output directory structure
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir = self.output_dir / "images"
        self.images_dir.mkdir(exist_ok=True)
        
        if verbose:
            print(f"✓ Output directory: {output_dir}")
    
    def build_document(
        self,
        contents_per_page: List[List[ExtractedContent]],
        blocks_per_page: List[List[LayoutBlock]],
        document_info: Optional[Dict] = None,
    ) -> Path:
        """
        Build complete LaTeX document.
        
        Args:
            contents_per_page: Extracted content for each page
            blocks_per_page: Layout blocks for each page (for metadata)
            document_info: Optional document metadata
            
        Returns:
            Path to main.tex file
        """
        if self.verbose:
            print(f"\n→ Building LaTeX document...")
        
        # Create document structure
        doc = TeXDocument()
        if document_info:
            doc.title = document_info.get("title", doc.title)
            doc.author = document_info.get("author", doc.author)
        
        # Generate LaTeX content (minimal mode)
        tex_content = self._generate_preamble(doc, minimal=True)
        tex_content += "\n\\begin{document}\n\n"
        tex_content += self._generate_title_page(doc, skip=True)
        tex_content += "\n"
        
        # Process each page
        for page_num, (contents, blocks) in enumerate(zip(contents_per_page, blocks_per_page), 1):
            if self.verbose:
                print(f"  Page {page_num}: {len(contents)} blocks")
            
            page_tex = self._generate_page(page_num, contents, blocks)
            tex_content += page_tex
            tex_content += "\n\\newpage\n\n"
            
            # Store metadata
            doc.pages.append({
                "page_num": page_num,
                "blocks": len(blocks),
                "text_blocks": sum(1 for c in contents if c.text),
                "latex_blocks": sum(1 for c in contents if c.latex),
                "image_blocks": sum(1 for c in contents if c.image_path),
            })
        
        tex_content += "\\end{document}\n"
        
        # Write main.tex
        main_tex_path = self.output_dir / "main.tex"
        with open(main_tex_path, "w", encoding="utf-8") as f:
            f.write(tex_content)
        
        # Write metadata
        meta_path = self.output_dir / "meta.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({
                "title": doc.title,
                "author": doc.author,
                "date": doc.date,
                "total_pages": len(doc.pages),
                "pages": doc.pages,
                "generated_by": "HeySeen v0.1.0",
                "timestamp": datetime.now().isoformat(),
            }, f, indent=2, ensure_ascii=False)
        
        if self.verbose:
            print(f"✓ LaTeX document created: {main_tex_path}")
            print(f"✓ Metadata saved: {meta_path}")
        
        return main_tex_path
    
    def _generate_preamble(self, doc: TeXDocument, minimal: bool = True) -> str:
        """Generate LaTeX preamble with packages and settings"""
        if minimal:
            # Minimal preamble for clean comparison
            preamble = r"""\documentclass[12pt,a4paper]{article}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{geometry}
\geometry{margin=2.5cm}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}

"""
        else:
            # Full preamble with all features
            preamble = r"""\documentclass[12pt,a4paper]{article}

% Essential packages
%\usepackage[utf8]{inputenc}
%\usepackage[T1]{fontenc}
%\usepackage[vietnamese]{babel}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{graphicx}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{geometry}

% Page layout
\geometry{margin=2.5cm}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}

% Hyperref settings
\hypersetup{
    colorlinks=true,
    linkcolor=blue,
    urlcolor=blue,
    citecolor=blue
}

% Custom commands
\newcommand{\blocktitle}[1]{\textbf{\large #1}\par\vspace{6pt}}
\newcommand{\blockcaption}[1]{\textit{#1}\par\vspace{4pt}}

"""
        return preamble
    
    def _generate_title_page(self, doc: TeXDocument, skip: bool = True) -> str:
        """Generate title page (optional)"""
        if skip:
            return ""  # No title page for clean comparison
        
        return f"""\\title{{{doc.title}}}
\\author{{{doc.author}}}
\\date{{{doc.date}}}
\\maketitle

\\tableofcontents
\\newpage

"""
    
    def _generate_page(
        self,
        page_num: int,
        contents: List[ExtractedContent],
        blocks: List[LayoutBlock],
    ) -> str:
        """Generate LaTeX for a single page with smart merging"""
        page_tex = f"% Page {page_num}\n"
        
        # Merge consecutive text blocks into paragraphs
        merged_items = self._merge_text_blocks(contents, blocks)
        
        # Extract first title as section heading
        first_title = None
        for item in merged_items[:]: # Iterate over a copy to allow modification
            if item and item.get('type') == 'title':
                first_title = item['text']
                merged_items.remove(item)
                break
        
        if first_title:
            page_tex += f"\\section*{{{self._escape_latex(first_title)}}}\n\n"
        # Removed auto-generated Page section
        
        # Generate content with structure awareness
        in_list = False
        for item in merged_items:
            if item['type'] == 'title':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                page_tex += f"\\subsection*{{{self._escape_latex(item['text'])}}}\n\n"
            
            elif item['type'] == 'section':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                page_tex += f"\\section{{{self._escape_latex(item['text'])}}}\n\n"
            
            elif item['type'] == 'subsection':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                page_tex += f"\\subsection{{{self._escape_latex(item['text'])}}}\n\n"
            
            elif item['type'] == 'list-item':
                # Open list if needed
                if not in_list:
                    page_tex += "\\begin{itemize}\n"
                    in_list = True
                # Remove bullet/number from text
                text = item['text'].lstrip('•-* ').lstrip('0123456789.abcABC.) ')
                page_tex += f"  \\item {self._escape_latex(text)}\n"
            
            elif item['type'] == 'paragraph':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                # Add paragraph with proper spacing
                escaped = self._escape_latex(item['text'])
                page_tex += f"{escaped}\n\n"
            elif item['type'] == 'math':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                # latex is already cleaned (no outer $$ delimiters)
                latex = item['latex'].strip()
                if latex:  # Skip empty math blocks
                    page_tex += f"\\[\\n{latex}\\n\\]\n\n"
            
            elif item['type'] == 'table':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                # Insert table latex directly
                if item['latex']:
                    page_tex += f"\n{item['latex']}\n\n"
            
            elif item['type'] == 'image':
                # Close any open list
                if in_list:
                    page_tex += "\\end{itemize}\n\n"
                    in_list = False
                image_path = Path(item['image_path'])
                rel_path = image_path.relative_to(self.output_dir) if image_path.is_absolute() else image_path
                
                page_tex += f"\\begin{{figure}}[h]\n"
                page_tex += f"  \\centering\n"
                page_tex += f"  \\includegraphics[width=0.8\\textwidth]{{{rel_path}}}\n"
                page_tex += f"  \\caption{{Figure from page {page_num}}}\n"
                page_tex += f"\\end{{figure}}\n\n"
        
        # Close any remaining open list
        if in_list:
            page_tex += "\\end{itemize}\n\n"
        
        return page_tex
    
    def _merge_text_blocks(
        self,
        contents: List[ExtractedContent],
        blocks: List[LayoutBlock],
    ) -> List[Dict]:
        """
        Merge consecutive text blocks into paragraphs with structure awareness.
        
        Breaks paragraphs when:
        - Encountering math/images
        - Large vertical gap (> 2x line height)
        - Horizontal position change (column switch)
        - Structure change (title/section/text)
        """
        merged = []
        current_paragraph = []
        prev_block = None
        
        import re
        noise_pattern = re.compile(r'^\s*\d+\s*$')
        eq_num_pattern = re.compile(r'^\s*[\(\[](\d+(\.\d+)*)[\)\]]\s*$')
        
        # Pattern to detect "Title 1" -> "1 Title" (Reading order fix)
        # Matches: Any text (non-dot end) + space + Number (e.g. "1", "2.1")
        # Excludes "Equation 1" if it might be a reference, but generally for headers this is safe
        trailing_num_re = re.compile(r'^([^\.]+?)\s+(\d+(\.\d+)*)$')

        for content, block in zip(contents, blocks):
            # 0. Noise Cleaning (Standalone Page Numbers)
            if content.text and noise_pattern.match(content.text):
                # Only if at very top or bottom of page (approx)
                if block.bbox.y0 < 0.1 or block.bbox.y0 > 0.9:
                    continue
            
            # 0.1 Structural Repair (Reading Order Swaps)
            if content.text and len(content.text) < 80:
                # Check for "Text Number" pattern
                m = trailing_num_re.match(content.text.strip())
                if m:
                    text_part = m.group(1).strip()
                    num_part = m.group(2)
                    # Heuristic: Only swap if text looks like a title (starts capital) 
                    # or contains Header keywords
                    if text_part and (text_part[0].isupper() or "Trang" in text_part):
                        content.text = f"{num_part} {text_part}"

            # 0.5 Tagging Detection (Eq Number detection)
            if content.text and eq_num_pattern.match(content.text):
                tag_match = eq_num_pattern.match(content.text)
                tag_val = tag_match.group(1)
                
                # Attach to PREVIOUS element if possible
                if current_paragraph:
                    # Append as string, though this is rare inside paragraph unless inline
                    # Better to treat as display math tag?
                    # If current paragraph is open, just append it? No, tags go on Math.
                    # If this line is JUST a number, it shouldn't break the paragraph?
                    # OR if we just finished a math block?
                    pass
                
                # Check if we should attach to the LAST added merged item (likely a math block)
                # Flush current paragraph first?
                if not current_paragraph and merged and merged[-1]['type'] == 'math':
                     # We can't easily inject \tag into texify output string without parsing.
                     # But we can append \tag{} to the latex string.
                     last_item = merged[-1]
                     # Check if it already has a tag?
                     if 'latex' in last_item:
                         last_item['latex'] += f" \\tag{{{tag_val}}}"
                         continue # Consumed this block
            
            # Calculate gap and decide whether to break paragraph
            should_break = False
            
            if prev_block and current_paragraph:
                # 1. Physical Layout Checks
                v_gap = block.bbox.y0 - prev_block.bbox.y1
                x_diff = abs(block.bbox.x0 - prev_block.bbox.x0)
                
                is_large_gap = v_gap > 0.04          # > 4% page height
                is_huge_gap = v_gap > 0.10           # > 10% page height (definite break)
                is_col_change = x_diff > 0.10        # > 10% page width
                
                # 2. Structure/Type Check
                # Ignore trivial type changes (e.g. Text -> Section-header) if sentence continues
                start_structure_element = False
                
                # 3. Linguistic Check (Sentence Continuity)
                prev_text = current_paragraph[-1].strip()
                # Check if previous line ends with sentence terminator
                ends_sentence = prev_text.endswith(('.', '!', '?', ':')) or prev_text.endswith(('."', '!"', '?"'))
                ends_hyphen = prev_text.endswith('-')
                
                # --- DECISION LOGIC ---
                if is_col_change:
                    should_break = True
                elif is_huge_gap:
                    should_break = True
                elif ends_hyphen:
                    should_break = False  # Always merge hyphenated lines
                elif not ends_sentence:
                    # Sentence definitely continues (no punctuation)
                    # Force merge unless gap is suspicious
                    if is_large_gap:
                        should_break = True # Gap too big for mid-sentence
                    else:
                        should_break = False # Merge!
                else:
                    # Sentence ended. 
                    # Break if gap is visible OR structure changes
                    if is_large_gap:
                        should_break = True
                    elif block.block_type != prev_block.block_type:
                        should_break = True
            
            if content.text:
                # Check block type for special handling
                block_classification = self._classify_text_block(block, content.text)
                
                # Handle structural elements (title, section, etc.)
                if block_classification in ["title", "section", "subsection", "list-item"]:
                    # Flush current paragraph
                    if current_paragraph:
                        merged.append({
                            'type': 'paragraph',
                            'text': ' '.join(current_paragraph)
                        })
                        current_paragraph = []
                    
                    # Add structured element
                    # Normalize text for headers too
                    clean_text = " ".join(content.text.split())
                    merged.append({
                        'type': block_classification,
                        'text': clean_text,
                        'metadata': {
                            'raw_label': block.raw_label,
                            'font_size': block.font_size,
                            'is_bold': block.is_bold
                        }
                    })
                    prev_block = block
                else:
                    # Regular text - break paragraph if needed
                    if should_break and current_paragraph:
                        merged.append({
                            'type': 'paragraph',
                            'text': ' '.join(current_paragraph)
                        })
                        current_paragraph = []
                    
                    # Accumulate text for paragraph
                    # Normalize whitespace to prevent accidental line breaks
                    clean_text = " ".join(content.text.split())
                    current_paragraph.append(clean_text)
                    prev_block = block
            
            elif content.latex:
                # Flush paragraph before math
                if current_paragraph:
                    merged.append({
                        'type': 'paragraph',
                        'text': ' '.join(current_paragraph)
                    })
                    current_paragraph = []
                
                # Distinguish between math and table
                block_type = 'table' if block.block_type == 'table' else 'math'
                merged.append({
                    'type': block_type,
                    'latex': content.latex
                })
                prev_block = block
            
            elif content.image_path:
                # Flush paragraph before image
                if current_paragraph:
                    merged.append({
                        'type': 'paragraph',
                        'text': ' '.join(current_paragraph)
                    })
                    current_paragraph = []
                
                merged.append({
                    'type': 'image',
                    'image_path': content.image_path
                })
        
        # Flush remaining paragraph
        if current_paragraph:
            merged.append({
                'type': 'paragraph',
                'text': ' '.join(current_paragraph)
            })
        
        return merged
    
    def _classify_text_block(self, block: LayoutBlock, text: str) -> str:
        """
        Classify text block based on structure metadata.
        
        Combines:
        1. Surya's raw_label (Title, Section-header, etc.)
        2. Font size estimation
        3. Text length + position heuristics
        
        Returns:
            One of: "title", "section", "subsection", "list-item", "text"
        """
        # CRITICAL: Prioritize Surya labels FIRST (most reliable)
        # But verify with text content check (avoid classifying lowercase text as section)
        text_start = text.strip()
        is_lowercase_start = text_start and text_start[0].islower()
        
        if block.raw_label:
            label = block.raw_label
            if label == "Title":
                return "title"
            elif label == "Section-header":
                 # Downgrade to text if it starts with lower case (misclassification)
                if is_lowercase_start:
                    return "text"
                return "section"
            elif label == "List-item":
                return "list-item"
            # If Text or other, continue to heuristics
        
        # Don't classify math content as sections
        if '$' in text or '\\[' in text or '\\(' in text:
            return "text"
            
        # Don't classify lowercase starting lines as sections (continuation of prev line)
        if is_lowercase_start:
            return "text"
            
        # Regex-based Section Detection (Suggestion Feature)
        # Matches: 1. Title, 1.1 Subtitle, A. Part A, I. Roman
        import re
        section_pattern = r'^(\d+(\.\d+)*|[IVX]+\.|[A-Z]\.)\s+[A-ZÀ-Ỹ]'
        if re.match(section_pattern, text_start) and len(text_start) < 80:
            # Count dots to determine level for numeric sections
            if re.match(r'^\d', text_start):
                 dot_count = text_start.split(' ')[0].count('.')
                 if dot_count > 1:
                     return "subsection"
            return "section"
        
        text_len = len(text.strip())
        
        # Very strict section detection:
        # Must be SHORT (<80 chars) AND in upper page
        if text_len < 80 and block.bbox.y0 < 0.3:
            # Check font size if available  
            if block.font_size:
                # Strong indicators: bold + large font
                if block.is_bold and block.font_size > 16:
                    return "title"
                elif block.is_bold and block.font_size > 13:
                    return "section"
                # Font size alone (without bold) - must be very large
                elif block.font_size > 20:
                    return "title"
                elif block.font_size > 17:
                    return "section"
            
            # Position-based fallback: ONLY for very top + short text + NO font data
            # This should rarely trigger if font analyzer is working
            if not block.font_size:
                if block.bbox.y0 < 0.05 and text_len < 40:
                    return "title"
                elif text_len < 30 and block.bbox.y0 < 0.10:
                    return "section"
        
        # Check for list patterns
        text_start = text.strip()[:3]
        if text_start.startswith(("• ", "- ", "* ", "1.", "a.", "i.")):
            return "list-item"
        
        # Default: everything else is body text
        return "text"
    
    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters, preserving math content"""
        import re
        
        # Fix common Vietnamese encoding issues first
        text = self._fix_vietnamese_encoding(text)
        
        # Pattern to match <math> tags OR $...$ delimiters
        # Note: We use a non-greedy match for $...$ to avoid spanning multiple formulas
        # We also handle escaped \$ to allow money symbols, but for now simplify.
        math_pattern = r'(<math(?:\s+display="(?:block|inline)")?>.+?</math>|\$.+?\$|\\\(.+?\\\))'
        
        # Find all math sections (split text by these patterns)
        parts = re.split(math_pattern, text, flags=re.DOTALL)
        
        result = []
        for part in parts:
            if not part: continue
            
            # Check if this part is a math block
            if part.startswith('<math') or part.startswith('$') or part.startswith(r'\('):
                 # It's math, don't escape content (except normalizing delimiters)
                 if part.startswith('<math'):
                     content = re.search(r'>((?:.|\n)+?)</math>', part).group(1)
                     is_display = 'display="block"' in part
                 elif part.startswith('$'):
                     content = part.strip('$')
                     is_display = False # Assume inline for single $
                 else:
                     content = part[2:-2]
                     is_display = False
                 
                 # Clean math
                 # Don't clean_math for inline simple variables to avoid heavy regex on small things?
                 # content = self._clean_math(content) 
                 
                 if is_display:
                     result.append(f"\n\\[ {content} \\]\n")
                 else:
                     result.append(f"${content}$")
            else:
                 # It's text, process rich text and escape
                 result.append(self._process_rich_text(part))
        
        final_text = "".join(result)
        
        # Restore structural placeholders
        final_text = final_text.replace("[[ITEM]]", "\n\\item ")
        
        return final_text

    def _process_rich_text(self, text: str) -> str:
        """Handle HTML-like tags in text (<b>, <i>) and escape the rest"""
        import re
        
        # Remove any stray <math> tags that weren't caught (e.g. malformed or inside text)
        text = re.sub(r'</?math.*?>', '', text)
        
        # Split by bold and italic tags
        # Note: This is a simple parser, doesn't handle nesting perfectly but works for OCR output
        parts = re.split(r'(<b>.*?</b>|<i>.*?</i>)', text, flags=re.DOTALL)
        
        result = []
        for part in parts:
            if part.startswith('<b>') and part.endswith('</b>'):
                content = part[3:-4]
                result.append(r'\textbf{' + self._escape_simple(content) + '}')
            elif part.startswith('<i>') and part.endswith('</i>'):
                content = part[3:-4]
                result.append(r'\textit{' + self._escape_simple(content) + '}')
            else:
                result.append(self._escape_simple(part))
                
        return "".join(result)
    
    def _fix_vietnamese_encoding(self, text: str) -> str:
        """Fix common Vietnamese encoding issues and OCR formatting errors"""
        import re
        
        # 1. Fix escaped characters that should be Unicode
        replacements = {
            r"n\\'eu": "nếu",
            r"\\'": "'",
        }
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)

        # 2. Fix common OCR Hallucinations & Broken Vietnamese (Fuzzy replacements)
        # Use regex boundary \b where appropriate
        ocr_fixes = {
            # Characters
            r"\bNhửn diửn\b": "Nhận diện",
            r"\bkứ hứu\b": "ký hiệu",
            r"\bký h iệu\b": "ký hiệu",
            r"toận": "toán",
            r"thuộng": "thường",
            r"Phân biửt": "Phân biệt",
            r"chử": "chữ",
            
            # Suggested Fixes
            r"h\.t\.d": "h.t.đ",
            r"v'oi": "với",
            r"công thúc": "công thức",
            r"đinh lý": "định lý",
            r"già sử": "giả sử",
            r"mênh đề": "mệnh đề",
            r"hàm sô": "hàm số",
            
            # Common OCR Errors
            r"vửét": "viết",
            r"công thức": "công thức", # normalize if needed
            r"đirợc": "được",
            r"dược": "được",
            r"cùa": "của",
            r"với": "với",
            
            # Common Math-context words
            r"\bma trân\b": "ma trận",
            r"\bĐinh nghĩa\b": "Định nghĩa",
            r"\bDjnh nghia\b": "Định nghĩa",
            r"\bDinh ly\b": "Định lý",
            r"\bBô dề\b": "Bổ đề",
            r"\bHê quả\b": "Hệ quả",
            
            # Specific Math Fixes (Group Theory)
            # Fix italic 'g' recognized as 'q' in Texify
            r"q\s*\\in\s*G": r"g \\in G",
            r"q\s*h\s*q\^{-1}": r"g h g^{-1}",
            r"qhq\^{-1}": r"ghg^{-1}",
            
            # Missing Integrals (Gauss Theorem context)
            r"=_{\\partial V}": r"= \\oiint_{\\partial V}",
            r"=_{\\partial S}": r"= \\oint_{\\partial S}",
            
            # Broken formatting
            r"•": "[[ITEM]]",  # Convert bullet points to placeholder
                             # (Will be restored to \item after escaping)
        }
        
        for pattern, replacement in ocr_fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _clean_math(self, math: str) -> str:
        """Clean up math LaTeX for better formatting"""
        import re
        
        # Add space in differentials: dx → d x
        math = re.sub(r'\bd([xyz])\b', r'd \1', math)
        
        # Use \to instead of \rightarrow for consistency with Mathpix style
        # (Actually both are fine, but keep our current \to)
        
        return math.strip()
    
    def _escape_simple(self, text: str) -> str:
        """Escape basic LaTeX special characters"""
        replacements = {
            "\\": "\\textbackslash{}",
            "&": "\\&",
            "%": "\\%",
            "$": "\\$",
            "#": "\\#",
            "_": "\\_",
            "{": "\\{",
            "}": "\\}",
            "~": "\\textasciitilde{}",
            "^": "\\textasciicircum{}",
            "<": "\\textless{}",
            ">": "\\textgreater{}",
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text


def build_tex_document(
    contents_per_page: List[List[ExtractedContent]],
    blocks_per_page: List[List[LayoutBlock]],
    output_dir: Path,
    document_info: Optional[Dict] = None,
    verbose: bool = True,
) -> Path:
    """
    Convenience function to build a LaTeX document.
    
    Args:
        contents_per_page: Extracted content for each page
        blocks_per_page: Layout blocks for each page
        output_dir: Directory to save output files
        document_info: Optional document metadata
        verbose: Print progress messages
        
    Returns:
        Path to main.tex file
    """
    builder = TeXBuilder(output_dir, verbose=verbose)
    return builder.build_document(contents_per_page, blocks_per_page, document_info)
