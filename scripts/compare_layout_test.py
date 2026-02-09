
import re
import sys
from pathlib import Path

def analyze_tex(tex_content):
    stats = {
        'title': bool(re.search(r'\\title\{', tex_content)),
        'author': bool(re.search(r'\\author\{', tex_content)),
        'maketitle': bool(re.search(r'\\maketitle', tex_content)),
        'abstract_env': bool(re.search(r'\\begin\{abstract\}', tex_content)),
        'section_count': len(re.findall(r'\\section\*?\{', tex_content)),
        'subsection_count': len(re.findall(r'\\subsection\*?\{', tex_content)),
        'subsubsection_count': len(re.findall(r'\\subsubsection\*?\{', tex_content)),
        'theorem_env': bool(re.search(r'\\begin\{theorem\}', tex_content)),
        'proof_env': bool(re.search(r'\\begin\{proof\}', tex_content)) or bool(re.search(r'\\begin\{proof_custom\}', tex_content)),
        'appendix': bool(re.search(r'P[Hh][Ụụ]\s*L[Ụụ][Cc]', tex_content, re.IGNORECASE)),
        'bibliography': bool(re.search(r'\\begin\{thebibliography\}', tex_content)),
        'math_display': len(re.findall(r'\\\[', tex_content)) + len(re.findall(r'\$\$', tex_content)) + len(re.findall(r'\\begin\{equation\}', tex_content)),
    }
    return stats

def main():
    if len(sys.argv) < 3:
        print("Usage: python script.py <generated_tex> <original_tex>")
        return

    gen_path = Path(sys.argv[1])
    orig_path = Path(sys.argv[2])

    print(f"Comparing:")
    print(f"Generated: {gen_path}")
    print(f"Original : {orig_path}")
    print("-" * 40)

    try:
        with open(gen_path, 'r', encoding='utf-8') as f:
            gen_content = f.read()
        with open(orig_path, 'r', encoding='utf-8') as f:
            orig_content = f.read()
    except Exception as e:
        print(f"Error reading files: {e}")
        return

    gen_stats = analyze_tex(gen_content)
    orig_stats = analyze_tex(orig_content)

    # Specific Checks based on "test_layout.tex"
    print(f"{'Feature':<20} | {'Generated':<10} | {'Original':<10} | {'Status':<10}")
    print("-" * 60)
    
    features = [
        ('Abstract Env', 'abstract_env'),
        ('Theorem Env', 'theorem_env'),
        ('Proof Env', 'proof_env'),
        ('Sections', 'section_count'),
        ('Subsections', 'subsection_count'),
        ('Subsubsections', 'subsubsection_count'),
        ('Display Math', 'math_display'),
        ('Appendix', 'appendix'),
    ]

    score = 0
    total = 0

    for label, key in features:
        gen_val = gen_stats[key]
        orig_val = orig_stats[key]
        
        # For counts, we accept if it's close or exact, depending on implementation
        status = "❌"
        if isinstance(gen_val, bool):
            if gen_val == orig_val:
                status = "✅"
                score += 1
            elif orig_val and not gen_val:
                status = "MISSING"
        else:
            # For counts types
            if gen_val == orig_val:
                status = "✅"
                score += 1
            else:
                status = f"DIFF ({gen_val-orig_val})"
                
        total += 1
        print(f"{label:<20} | {str(gen_val):<10} | {str(orig_val):<10} | {status}")

    print("-" * 60)
    
    # Text Analysis check for "Swallowed Section" issue
    # The fix was to prevent long paragraphs from becoming sections.
    # We check if there are any suspicious long sections in generated file.
    long_sections = []
    for m in re.finditer(r'\\section\*?\{(.*?)\}', gen_content):
        title_text = m.group(1)
        if len(title_text.split()) > 20: 
            long_sections.append(title_text[:50] + "...")
    
    if long_sections:
        print("\n[WARNING] Found potentially swallowed section headers (>20 words):")
        for s in long_sections:
            print(f"  - {s}")
    else:
        print("\n[PASS] No overly long section headers found (Section Splitter works).")

    # Check for Explicit Appendix
    if "PHỤ LỤC" in gen_content and "\\section*" in gen_content:
        print("[PASS] found PHỤ LỤC section.")
    
    # Check for Vietnamese Typo Fixes
    typos_to_check = ['với', 'h.t.đ', 'Phương trình']
    print("\nChecking Typo Fixes:")
    for word in typos_to_check:
        if word in gen_content:
            print(f"  - '{word}': Found ✅")
        else:
            print(f"  - '{word}': Not Found (Maybe not in text or not fixed) ❓")

if __name__ == "__main__":
    main()
