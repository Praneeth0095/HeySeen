import requests
import json
import re

text = r"""
% Page 1
\section*{Page 1}

Phân tích sự hội tụ của các thuật toán tối ưu hóa bậc cao trong không gian Hilbert HeySeen Research Group Mac Mini M2 Pro Computing Lab February 5, 2026 Abstract Gradient Descent cải tiến. Chúng tôi cung cấp các chứng minh toán học chặt chẽ và kết quả mô phỏng số để đánh giá hiệu suất của hệ thống HeySeen OCR trong việc xử lý các tài liệu học thuật dài hơi. Đặc biệt, chúng tôi tập trung vào các phương pháp tối ưu momentum và các biến thể adaptive learning rate như Adam, RMSprop, và AdaGrad trong không gian vô hạn chiều.
"""

prompt = f"""Bạn là một trợ lý biên tập LaTeX chuyên nghiệp. Nhiệm vụ của bạn là sửa lỗi chính tả và ngữ pháp tiếng Việt trong đoạn văn bản sau đay (do OCR tạo ra).

QUY TẮC TUYỆT ĐỐI (QUAN TRỌNG):
1. GIỮ NGUYÊN tất cả các lệnh LaTeX (bắt đầu bằng \\ như \\section, \\item, \\textbf...).
2. GIỮ NGUYÊN tất cả nội dung toán học (nằm trong $...$, $$...$$, \\( ... \\), \\[ ... \\]).
3. KHÔNG thay đổi cấu trúc văn bản.
4. CHỈ sửa các từ tiếng Việt bị sai chính tả (ví dụ: "djnh nghia" -> "định nghĩa", "tính lới" -> "tính lồi").
5. KHÔNG thêm bất kỳ lời dẫn chuyện nào. CHỈ trả về code LaTeX đã sửa.

Văn bản gốc:
```latex
{text}
```

Văn bản đã sửa:
"""

payload = {
    "model": "qwen2.5-coder:7b",
    "prompt": prompt,
    "stream": False,
    "options": {
        "temperature": 0.1,
        "num_ctx": 4096
    }
}

try:
    print("Sending request...")
    response = requests.post("http://localhost:11434/api/generate", json=payload, timeout=60)
    response.raise_for_status()
    result = response.json()
    corrected_text = result.get('response', '').strip()
    
    print("--- RAW RESPONSE START ---")
    print(corrected_text)
    print("--- RAW RESPONSE END ---")
    
    # Simulate cleaning
    match = re.search(r'```(?:latex)?\n(.*?)```', corrected_text, re.DOTALL)
    if match:
        cleaned = match.group(1)
        print("--- CLEANED RESPONSE ---")
        print(len(cleaned))
    else:
        print("No code block found.")
        print(len(corrected_text))

except Exception as e:
    print(e)
