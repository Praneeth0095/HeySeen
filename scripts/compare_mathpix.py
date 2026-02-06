import re
import math
from difflib import SequenceMatcher

def read_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()

def normalize(text):
    """Normalize text for rigorous Mathpix vs HeySeen comparison"""
    # Remove latex commands to focus on content
    text = re.sub(r'\\[a-zA-Z]+(\*?)', '', text) 
    # Remove braces and formatting chars
    text = re.sub(r'[\{\}\[\]\(\)\$\^_\*\&]', '', text)
    # Remove tags like (1), (2)
    text = re.sub(r'\(\d+\)', '', text)
    # Lowercase and whitespace
    text = re.sub(r'\s+', ' ', text).strip().lower()
    return text

def normalize_math(latex):
    """Normalize extracted math formulas"""
    s = latex
    # Remove environments
    s = re.sub(r'\\begin\{.*?\}.*?', '', s)
    s = re.sub(r'\\end\{.*?\}', '', s)
    # Remove whitespace
    s = "".join(s.split())
    # Standardize common variations
    replacements = [
        (r'\left(', '('), (r'\right)', ')'),
        (r'\left[', '['), (r'\right]', ']'),
        (r'\left\{', '{'), (r'\right\}', '}'),
        (r'^{\prime}', "'"), (r"''", "'"),
        (r'dx', 'd x'), (r'dt', 'd t'),
        (r'\text', '\mathrm'),
        (r'\operatorname', ''),
        (r'd\theta', r'd \theta'),
    ]
    for old, new in replacements:
        s = s.replace(old, new)
    return s

def compare_mathpix_vs_heyseen():
    mathpix_path = "mathpix_results/mathpix_2columns.tex"
    heyseen_path = "examples/test_2col_v2/main.tex"
    
    mp_content = read_file(mathpix_path)
    hs_content = read_file(heyseen_path)
    
    print("=== HeySeen vs Mathpix Benchmark (2-Column PDF) ===\n")
    
    # 1. Structural Similarity (Normalized Text)
    # ------------------------------------------
    mp_norm = normalize(mp_content)
    hs_norm = normalize(hs_content)
    
    ratio = SequenceMatcher(None, mp_norm, hs_norm).ratio()
    print(f"Content Similarity: {ratio:.2%}")
    if ratio > 0.90:
        print("  ✅ Excellent Content Match (>90%)")
    elif ratio > 0.80:
        print("  ✓ Good Content Match (>80%)")
    else:
        print("  ⚠️ Significant Content Differences")
        
    print(f"  Mathpix Length: {len(mp_norm)} chars")
    print(f"  HeySeen Length: {len(hs_norm)} chars")
    
    # 2. Key Formula Check
    # --------------------
    print("\nFormula Fidelity Check:")
    
    # Dictionary of key math fragments to look for
    key_math = {
        "State Equation": r"\dot{x}(t)=Ax(t)+Bu(t)",
        "Lyapunov": r"V(x)=x^{T}Px",
        "Riccati": r"A^{T}P+PA-PBR^{-1}B^{T}P+Q=0",
        "Runge-Kutta 1": r"k_{1}=hf(t_{n},y_{n})",
        "Runge-Kutta 4": r"k_{4}=hf(t_{n}+h,y_{n}+k_{3})",
        "Update Rule": r"y_{n+1}=y_{n}+\frac{1}{6}",
        "Wide Integral": r"\mathcal{I}=\int_{-\infty}^{\infty}\int_{-\infty}^{\infty}e^{-(x^{2}+y^{2})}"
    }
    
    hs_math_norm = normalize_math(hs_content)
    
    matches = 0
    for name, pattern in key_math.items():
        pat_norm = normalize_math(pattern)
        # Fuzzy check via substring
        # Check if a sufficiently similar string exists in HeySeen
        
        # Simple substring check first
        if pat_norm in hs_math_norm:
            print(f"  ✅ {name}: Perfect Match")
            matches += 1
        else:
            # Try fuzzy matching against lines in HS
            # This is expensive but accurate
            found_fuzzy = False
            # Break HS into chunks
            hs_chunks = hs_content.split('$$') + hs_content.split('\\[') + hs_content.split('\\]')
            for chunk in hs_chunks:
                c_norm = normalize_math(chunk)
                if SequenceMatcher(None, pat_norm, c_norm).ratio() > 0.85:
                     print(f"  ✅ {name}: Fuzzy Match ({SequenceMatcher(None, pat_norm, c_norm).ratio():.2f})")
                     matches += 1
                     found_fuzzy = True
                     break
            if not found_fuzzy:
                print(f"  ❌ {name}: Missing or Malformed")
                # print(f"     Target: {pat_norm}")
                
    print(f"\nFormula Accuracy: {matches}/{len(key_math)}")
    
    # 3. Reading Order Verification
    # -----------------------------
    print("\nReading Order Logic:")
    # Check if "Phương pháp số" comes AFTER "Mô hình toán học" (Left Col) 
    # AND "Kết quả thực nghiệm" comes AFTER "Phương pháp số" (Right Col)
    
    def get_pos(text, sub):
        return text.find(sub)
    
    idx_intro = get_pos(hs_norm, "mô hình toán học")
    idx_lyapunov = get_pos(hs_norm, "hàm năng lượng")
    idx_numerical = get_pos(hs_norm, "phương pháp số")
    idx_result = get_pos(hs_norm, "kết quả thực nghiệm")
    idx_appendix = get_pos(hs_norm, "phụ lục")
    
    flow_ok = True
    if idx_intro == -1 or idx_numerical == -1:
        print("  ⚠️ Could not find key section headers to verify order.")
        flow_ok = False
    else:
        if idx_intro < idx_numerical:
            print("  ✅ Left Col (Model) before Right Col (Numerical)")
        else:
            print("  ❌ INVERTED: Right Col appears before Left Col")
            flow_ok = False
            
        if idx_numerical < idx_result:
            print("  ✅ Right Col flow correct")
        else:
             print("  ❌ INVERTED: Results appear before Method")
             flow_ok = False
             
        if idx_result < idx_appendix:
             print("  ✅ Spanning Footer appears last")
        else:
             print("  ❌ INVERTED: Appendix appears too early")
             flow_ok = False

    if flow_ok:
        print("\n🏆 Conclusion: HeySeen is STRUCTURALLY EQUIVALENT to Mathpix.")
    else:
        print("\n⚠️ Conclusion: HeySeen still has layout issues compared to Mathpix.")

if __name__ == "__main__":
    compare_mathpix_vs_heyseen()
