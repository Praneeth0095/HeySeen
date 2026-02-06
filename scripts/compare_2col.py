import re
import math
from difflib import SequenceMatcher

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def normalize_text(text):
    """Normalize text for structural comparison"""
    # Remove LaTeX commands roughly to compare content flow
    text = re.sub(r'\\[a-zA-Z]+(\{[^}]*\})?', '', text)
    text = re.sub(r'[\$\{\}\[\]\(\)]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text.lower()

def extract_meaningful_chunks(latex_content):
    """
    Extract meaningful chunks of text/math to determine order.
    Returns list of dicts: {'type': 'text'|'math', 'content': str}
    """
    chunks = []
    
    # Simple parser: split by section headers or blank lines?
    # Actually, let's look for specific key phrases that indicate Reading Order
    
    key_phrases = [
        "tóm tắt: bài viết này thiết lập",
        "giới thiệu",
        "mô hình toán học",
        "hàm năng lượng",
        "ta định nghĩa hàm lyapunov",
        "thách thức về bố cục",
        "phương pháp số",
        "chúng ta sử dụng thuật toán",
        "giá trị tiếp theo được tính bởi",
        "kết quả thực nghiệm",
        "bảng dưới đây so sánh",
        "nhận diện cấu trúc nhanh nhờ surya",
        "kết luận",
        "phụ lục: công thức tràn cột"
    ]
    
    normalized = normalize_text(latex_content)
    
    found_order = []
    for phrase in key_phrases:
        idx = normalized.find(phrase)
        if idx != -1:
            found_order.append((idx, phrase))
        else:
            # Try fuzzy match
            pass
            
    # Sort by position
    found_order.sort(key=lambda x: x[0])
    return [x[1] for x in found_order]

def main():
    gt_path = "tests_original/test_2columns.tex"
    out_path = "examples/test_2col_v2/main.tex"
    
    try:
        gt_content = read_file(gt_path)
        out_content = read_file(out_path)
    except FileNotFoundError:
        print("Files not found. Run conversion first.")
        return

    print("=== 2-Column Text Flow Analysis ===\n")

    # 1. Formula Count Check
    # ----------------------
    # Specific formulas in 2-column test
    formulas_to_check = [
        r"\dot{x}(t)",
        r"V(x)",
        r"A^{T}P",
        r"f(x+h)",
        r"k_{1}",
        r"k_{2}",
        r"k_{3}",
        r"k_{4}",
        r"y_{n+1}",
        r"\mathcal{I}"
    ]
    
    # Normalize contents for math check
    def norm_math(s): return re.sub(r'\s', '', s)
    gt_norm = norm_math(gt_content)
    out_norm = norm_math(out_content)
    
    print("Formula Detection:")
    for f in formulas_to_check:
        f_norm = norm_math(f)
        found = f_norm in out_norm
        status = "✅ Found" if found else "❌ Missing"
        print(f"  {status} : {f}")

    print("\nReading Order Check:")
    gt_order = extract_meaningful_chunks(gt_content)
    out_order = extract_meaningful_chunks(out_content)
    
    # Since GT is defined by us, we assume extracted GT order is the ground truth
    print(f"  Ground Truth Sequence: {len(gt_order)} phrases")
    
    # Check if Out order matches GT order subsequence
    # We want to ensure that 'Left Column' phrases come before 'Right Column' phrases
    
    # Let's check inversions
    is_correct = True
    for i in range(len(gt_order)):
        if gt_order[i] not in out_order:
            print(f"  ❌ Missing Text Phrase: '{gt_order[i]}'")
            is_correct = False
            continue
            
        out_idx = out_order.index(gt_order[i])
        
        # Check relative order with previous found item
        if i > 0:
            prev_gt = gt_order[i-1]
            if prev_gt in out_order:
                prev_out_idx = out_order.index(prev_gt)
                if out_idx < prev_out_idx:
                    print(f"  ❌ Order Inversion (Wrong Column?):")
                    print(f"     Expected: '{prev_gt}' -> '{gt_order[i]}'")
                    print(f"     Found:    '{gt_order[i]}' ... '{prev_gt}'")
                    is_correct = False

    if is_correct:
         print("  ✅ Text Flow is Correct (Left-Col -> Right-Col -> Wide-Footer)")
    else:
         print("  ⚠️ Text Flow Errors Detected")
         
    # Similarity
    ratio = SequenceMatcher(None, gt_norm, out_norm).ratio()
    print(f"\nOverall Content Similarity: {ratio:.2%}")

if __name__ == "__main__":
    main()
