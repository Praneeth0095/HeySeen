1. Kiến trúc Pipeline "Đa luồng & Đa chuyên gia" (Routing Engine)
Hiện tại HeySeen đang quá phụ thuộc vào Texify cho mọi thứ. Texify rất giỏi Toán nhưng lại là "kẻ phá hoại" Tiếng Việt và tiêu đề.

Giải pháp: Sử dụng nhãn (Labels) từ Surya Layout Analysis để định tuyến (Routing):

Nếu nhãn là Title, Header, Text: Chuyển vùng ảnh đó qua một bộ OCR mạnh về ngôn ngữ (như PaddleOCR bản tiếng Việt hoặc Tesseract 5). Đừng để Texify chạm vào các vùng này.

Nếu nhãn là Formula: Đẩy qua Texify.

Nếu nhãn là Table: Đẩy qua một model chuyên dụng như Table Transformer (TATR).

2. Khắc phục lỗi "Nuốt nội dung" trong Section (Smart Parsing)
Lỗi mà HeySeen đang gặp (gộp cả đoạn văn vào trong \section{...}) là do bộ Parser chưa biết điểm dừng của tiêu đề.

Giải pháp - Quy tắc "Ngắt dòng vật lý": * Trong file JSON trả về từ Surya, mỗi Bounding Box có một tọa độ. Team cần lập trình: Mỗi lệnh \section chỉ được phép nhận nội dung của duy nhất một Bounding Box có nhãn Header/Title. * Tất cả nội dung thuộc Bounding Box tiếp theo phải được đẩy ra ngoài dấu ngoặc nhọn }.

Heuristic dựa trên độ dài: Thiết lập ngưỡng (Threshold). Nếu nội dung của một Section dài quá 15-20 từ, hệ thống phải tự động cắt đôi: lấy phần đầu làm tiêu đề, phần sau trả về văn bản thường.

3. "Dọn rác" và Xử lý Header/Footer tự động
HeySeen đang bị lẫn các số trang và tiêu đề lặp lại (running headers) vào giữa văn bản.

Giải pháp - Lọc theo tọa độ (Spatial Filtering):

Thiết lập một "Vùng an toàn" (Safe Zone) ở giữa trang (ví dụ từ 5% đến 95% chiều cao trang).

Mọi khối văn bản nằm ngoài vùng này (quá sát mép trên hoặc mép dưới) cần được kiểm tra: Nếu nó lặp lại ở nhiều trang hoặc chỉ chứa 1 chữ số đơn lẻ -> Xóa bỏ hoàn toàn.

4. Xử lý "Hallucination" và Tiếng Việt trong Toán
Texify thường xuyên biến các từ tiếng Việt ngắn (với, tại, khi, và) thành ký hiệu toán học lỗi.

Giải pháp - Lớp Fallback thông minh:

Sau khi Texify trả về kết quả, hãy chạy một bộ lọc Language Detection.

Nếu trong một khối "Toán" mà tỷ lệ ký tự Tiếng Việt (có dấu) chiếm trên 30%, hãy đánh dấu khối đó là "Nhận diện sai" và ra lệnh cho hệ thống chạy lại khối đó bằng bộ OCR văn bản thuần túy.

Hậu xử lý Ký tự đặc biệt: Xây dựng bảng ánh xạ (Mapping table) để chuyển đổi ngược các ký tự lỗi kinh điển: v'oi -> với, h.t.d -> h.t.đ.

5. Tái cấu trúc cấu trúc học thuật (Semantic Reconstruction)
Để file LaTeX có thể biên dịch (compile) được ngay, HeySeen cần thông minh hơn trong việc nhận diện môi trường.

Mục lục (TOC): Đừng cố OCR các dòng có dấu chấm. Team hãy lập trình: Nếu phát hiện vùng có cấu trúc giống Mục lục, hãy xóa sạch và thay bằng lệnh duy nhất \tableofcontents.

Định lý & Chứng minh (Theorems & Proofs): * Sử dụng nhãn Key-value để phát hiện các từ khóa ở đầu dòng (Theorem, Lemma, Proof).

Tự động bao bọc chúng bằng các môi trường chuẩn: \begin{theorem} ... \end{theorem}.

Số thứ tự công thức (Equation Numbers):

Sử dụng thuật toán Horizontal Proximity. Nếu một khối số (ví dụ: (1.1)) nằm ngang hàng với một khối Math, hãy dùng lệnh \tag{1.1} lồng bên trong khối Math đó thay vì để nó trôi nổi.

Tóm tắt hành động cho Team HeySeen:
Cải tiến layout_analyzer.py: Tích hợp tọa độ Bounding Box vào kết quả cuối để xác định điểm ngắt Section.

Thêm lớp engine_router.py: Phân phối vùng ảnh cho đúng chuyên gia (Toán -> Texify, Chữ -> PaddleOCR).

Hoàn thiện post_processor.py: Sửa lỗi thẻ HTML, dọn rác số trang và khôi phục môi trường LaTeX.

Đánh giá: Nếu thực hiện đúng 5 bước này, HeySeen sẽ khắc phục được 95% các lỗi hiện tại và có thể xử lý tốt mọi loại tài liệu từ sách giáo khoa đến báo cáo arXiv.