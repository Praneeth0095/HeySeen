
import re
import sys
from pathlib import Path
from difflib import SequenceMatcher

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return ""

def extract_math_blocks(content):
    """
    Extract display math blocks: \[...\], $$...$$, \begin{equation}...\end{equation}, \begin{align}...\end{align}
    """
    formulas = []
    
    # Pattern 1: \[ ... \]
    p1 = re.compile(r'\\\[(.*?)\\\]', re.DOTALL)
    formulas.extend(p1.findall(content))
    
    # Pattern 2: $$ ... $$
    p2 = re.compile(r'\$\$(.*?)\$\$', re.DOTALL)
    formulas.extend(p2.findall(content))
    
    # Pattern 3: environments
    envs = ['equation', 'align', 'align*', 'gather', 'gather*', 'multline', 'multline*']
    for env in envs:
        p3 = re.compile(r'\\begin\{' + re.escape(env) + r'\}(.*?)\\end\{' + re.escape(env) + r'\}', re.DOTALL)
        formulas.extend(p3.findall(content))
        
    return formulas

def normalize(latex):
    """Normalize latex string for comparison"""
    # Remove whitespace
    s = "".join(latex.split())
    
    # Common replacements
    replacements = [
        (r'\left(', '('), (r'\right)', ')'),
        (r'\left[', '['), (r'\right]', ']'),
        (r'\left\{', '{'), (r'\right\}', '}'),
        (r'\left|', '|'), (r'\right|', '|'),
        (r'\operatorname*', r'\operatorname'),
        (r'\operatorname{lim}', r'\lim'),
        (r'\to', r'\rightarrow'), # Standardize arrow
        (r'\dots', r'\ldots'), # Standardize dots
        (r'\cdots', r'\ldots'), # Standardize centered dots to ldots for comparison
        (r'^{\prime\prime}', r"''"), # Standardize double prime
        (r'^{\prime}', r"'"), # Standardize single prime
        (r'\ce', r'\mathrm'), # Treat chemical formulas as text/math
        # Text normalization for accuracy (Vietnamese accents)
        (r'đ', r'd'), (r'Đ', r'D'),
        (r'á', r'a'), (r'à', r'a'), (r'ả', r'a'), (r'ã', r'a'), (r'ạ', r'a'),
        (r'ă', r'a'), (r'ắ', r'a'), (r'ằ', r'a'), (r'ẳ', r'a'), (r'ẵ', r'a'), (r'ặ', r'a'),
        (r'â', r'a'), (r'ấ', r'a'), (r'ầ', r'a'), (r'ẩ', r'a'), (r'ẫ', r'a'), (r'ậ', r'a'),
        (r'é', r'e'), (r'è', r'e'), (r'ẻ', r'e'), (r'ẽ', r'e'), (r'ẹ', r'e'),
        (r'ê', r'e'), (r'ế', r'e'), (r'ề', r'e'), (r'ể', r'e'), (r'ễ', r'e'), (r'ệ', r'e'),
        (r'í', r'i'), (r'ì', r'i'), (r'ỉ', r'i'), (r'ĩ', r'i'), (r'ị', r'i'),
        (r'ó', r'o'), (r'ò', r'o'), (r'ỏ', r'o'), (r'õ', r'o'), (r'ọ', r'o'),
        (r'ô', r'o'), (r'ố', r'o'), (r'ồ', r'o'), (r'ổ', r'o'), (r'ỗ', r'o'), (r'ộ', r'o'),
        (r'ơ', r'o'), (r'ớ', r'o'), (r'ờ', r'o'), (r'ở', r'o'), (r'ỡ', r'o'), (r'ợ', r'o'),
        (r'ú', r'u'), (r'ù', r'u'), (r'ủ', r'u'), (r'ũ', r'u'), (r'ụ', r'u'),
        (r'ư', r'u'), (r'ứ', r'u'), (r'ừ', r'u'), (r'ử', r'u'), (r'ữ', r'u'), (r'ự', r'u'),
        (r'ý', r'y'), (r'ỳ', r'y'), (r'ỷ', r'y'), (r'ỹ', r'y'), (r'ỵ', r'y'),
        (r'\,', ''), (r'\;', ''), (r'\:', ''), (r'\ ', ''), # Remove spacing
        (r'\text', r'\mathrm'), # Treat text as rm
        (r'\iff', r'\Longleftrightarrow'), 
        (r'\implies', r'\Longrightarrow'),
        (r'\le', r'\leq'),
        (r'\ge', r'\geq'),
        (r'dx', r'd x'), # Texify often outputs "d x"
    ]
    
    for old, new in replacements:
        s = s.replace(old, new)
        
    # Remove label/tag
    s = re.sub(r'\\label\{.*?\}', '', s)
    s = re.sub(r'\\tag\{.*?\}', '', s)
    
    return s

def compare_lists(gt_list, out_list):
    """
    Compare two lists of formulas.
    Returns (matches, missing, total_gt)
    """
    # Use simple normalization first
    gt_norm = [normalize(f) for f in gt_list]
    out_norm = [normalize(f) for f in out_list]
    
    matches = 0
    missing_indices = []
    
    used_out_indices = set()
    
    for i, gt in enumerate(gt_norm):
        found = False
        # Try exact match
        for j, out in enumerate(out_norm):
            if j in used_out_indices:
                continue
            if gt == out:
                matches += 1
                used_out_indices.add(j)
                found = True
                break
        
        # Try fuzzy match if not found
        if not found:
            best_ratio = 0
            best_idx = -1
            
            for j, out in enumerate(out_norm):
                if j in used_out_indices:
                    continue
                ratio = SequenceMatcher(None, gt, out).ratio()
                if ratio > 0.85: # High threshold for "match"
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_idx = j
            
            if best_idx != -1:
                matches += 1
                used_out_indices.add(best_idx)
                found = True
                # print(f"  [Fuzzy Match] Ratio: {best_ratio:.2f}")
                # print(f"    GT:  {gt[:50]}...")
                # print(f"    OUT: {out_norm[best_idx][:50]}...")
        
        if not found:
            missing_indices.append(i)
            
    return matches, missing_indices, len(gt_list)

def main():
    print("=== HeySeen Comparison Results ===\n")
    
    tests = [1, 2, 3]
    total_matches = 0
    total_formulas = 0
    
    for test_id in tests:
        gt_path = f"tests_original/test_{test_id}_original.tex"
        out_path = f"examples/test_{test_id}/main.tex"
        
        gt_content = read_file(gt_path)
        out_content = read_file(out_path)
        
        gt_formulas = extract_math_blocks(gt_content)
        out_formulas = extract_math_blocks(out_content)
        
        print(f"Test {test_id}:")
        print(f"  GT Formulas: {len(gt_formulas)}")
        print(f"  Out Formulas: {len(out_formulas)}")
        
        matches, missing, total = compare_lists(gt_formulas, out_formulas)
        
        accuracy = (matches / total * 100) if total > 0 else 0
        print(f"  Matches: {matches}/{total}")
        print(f"  Accuracy: {accuracy:.1f}%")
        
        if missing:
            print("  Missing / Mismatched Formulas (Indices in GT):")
            for idx in missing:
                print(f"    - [{idx+1}] {gt_formulas[idx][:60].strip()}...")
                # Try to find closest candidate in output for debugging
                gt_norm = normalize(gt_formulas[idx])
                best_ratio = 0
                best_candidate = ""
                for out in out_formulas:
                    out_norm = normalize(out)
                    ratio = SequenceMatcher(None, gt_norm, out_norm).ratio()
                    if ratio > best_ratio:
                        best_ratio = ratio
                        best_candidate = out
                
                if best_ratio > 0.4:
                    print(f"      Closet Candidate (Sim={best_ratio:.2f}): {best_candidate[:60].strip()}...")
        
        print("-" * 40)
        total_matches += matches
        total_formulas += total
        
    global_accuracy = (total_matches / total_formulas * 100) if total_formulas > 0 else 0
    print(f"\nOverall Accuracy: {global_accuracy:.1f}% ({total_matches}/{total_formulas})")

if __name__ == "__main__":
    main()
