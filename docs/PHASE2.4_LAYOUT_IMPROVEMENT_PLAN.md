# Kế hoạch Cải tiến Nhận diện Layout cho HeySeen (Phase 2.4)

## 1. Phân tích Kết quả Test Hiện tại

Sau khi chạy thử nghiệm trên `pdf_examples/OCR_test_layout.pdf` và so sánh với `tests_original/test_layout.tex`, chúng tôi nhận thấy các vấn đề sau:

### A. Cấu trúc Tài liệu (Structure)
- **Title/Author/Date:** Hệ thống hiện tại nhận diện Date ("2026 February 9") là Section Header, trong khi Title thực sự ("Nghiên cứu về...") lại bị lẫn vào văn bản thường.
- **Abstract:** Không nhận diện được môi trường `abstract`. Nội dung hiển thị như văn bản thường bắt đầu bằng "Abstract Tóm tắt...".
- **Hierarchy (Phân cấp):** 
  - `subsection` được nhận diện tốt nhưng đôi khi bị nhầm lẫn.
  - `subsubsection` chưa được hỗ trợ tốt, thường bị gộp vào `subsection` hoặc văn bản thường.
- **Table of Contents (TOC):** Đang bị nhận diện nhầm là một **Table** (Bảng biểu) do cấu trúc dòng kẻ chấm (....) tạo thành lưới ảo.

### B. Môi trường Toán học & Học thuật (Environments)
- **Theorem/Proof:** Các môi trường `theorem`, `lemma`, `proof` chưa được nhận diện. Văn bản hiển thị dạng "Proof. Chứng minh..." thay vì `\begin{proof}`.
- **Appendix:** Phụ lục (`\appendix`) chưa được xử lý đặc biệt, dẫn đến việc đánh số section có thể bị sai hoặc mất cấu trúc "Phụ lục A".

### C. Bảng biểu (Tables)
- **False Positives:** Thuật toán "Table Recovery" quá nhạy, gộp các dòng văn bản rời rạc (như TOC hoặc danh sách) thành bảng.

## 2. Kế hoạch Cải tiến Chi tiết

### Giai đoạn 1: Tinh chỉnh Layout Analyzer (Đã thực hiện một phần)
- **Tăng cường Font Analysis:**
  - [x] Phân biệt `title`, `section`, `subsection`, `subsubsection` dựa trên kích thước font tương đối (Relative Font Size) và độ đậm (Bold weight).
  - [ ] **TODO:** Tinh chỉnh ngưỡng (threshold) để tránh nhận diện nhầm Date làm Section.
- **Cải thiện Table Detection:**
  - [x] Tăng độ khó cho thuật toán `_merge_table_fragments` (yêu cầu cấu trúc lưới rõ ràng hơn).
  - [ ] **TODO:** Thêm bộ lọc đặc biệt cho TOC (Table of Contents) để tránh gộp thành bảng.

### Giai đoạn 2: Post-Processing Logic (Xử lý Nội dung)
Cần bổ sung logic vào `ContentExtractor` hoặc `TexBuilder` để nhận diện các từ khóa ngữ nghĩa:
- **Abstract Check:** Nếu block đầu tiên sau Title bắt đầu bằng "Abstract" hoặc "Tóm tắt", gán type = `abstract`.
- **Theorem/Proof Check:** 
  - Regex tìm kiếm các mẫu: `^(Định lý|Theorem|Lemma|Bổ đề)\s+(\d+|\[.*\])`
  - Regex tìm kiếm: `^(Chứng minh|Proof)[.:]`
  - Chuyển đổi block tương ứng sang môi trường LaTeX `\begin{theorem} ... \end{theorem}`.

### Giai đoạn 3: Bibliography & Appendix
- **Appendix Helper:** Phát hiện keyword "Phụ lục" / "Appendix" ở cấp độ Section để chèn lệnh `\appendix`.
- **Reference Parsing:** Cải thiện logic tách danh mục tài liệu tham khảo (References) để tạo môi trường `thebibliography` thay vì danh sách thường.

## 3. Lộ trình Thực hiện
1. **Tuần 1:** Hoàn thiện Font Analysis cho phân cấp đề mục (Done).
2. **Tuần 1:** Fix lỗi nhận diện TOC là Table (High Priority).
3. **Tuần 2:** Implement Semantic Parsers cho Abstract, Theorem, Proof.
4. **Tuần 2:** Re-run benchmark layout test.

---
*Ghi chú: Các thay đổi cơ bản cho Giai đoạn 1 đã được áp dụng vào codebase (tinh chỉnh `detected_layout` và `font_analyzer`).*
