# 👁️ HeySeen: PDF → TeX + Images

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Platform: macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

> **Offline-first PDF to LaTeX converter optimized for Apple Silicon**

**HeySeen** chuyển đổi PDF (bài báo khoa học, sách chuyên ngành) thành **thư mục gồm file TeX và ảnh**, chạy **hoàn toàn offline trên macOS**. Không cần API cloud, không phụ thuộc subscription.

---

## ✨ Tính năng

- 🔒 **100% Offline**: Dữ liệu không rời khỏi máy bạn
- 🚀 **Tối ưu Apple Silicon**: Tận dụng Metal Performance Shaders (MPS)
- 📄 **PDF → LaTeX**: Chuyển đổi text, công thức toán, hình ảnh
- 🎯 **Layout Analysis**: Nhận dạng cấu trúc tài liệu (multi-column, figures, tables)
- 🧮 **Math OCR**: Nhận dạng công thức toán học → LaTeX
- 🖼️ **Image Extraction**: Tự động trích xuất và đặt tên hình ảnh
- 🌐 **Web Interface**: UI thân thiện để upload và xử lý PDF
- 🔧 **CLI Tool**: Command-line interface cho batch processing

### 🎯 Use Cases

- **Nghiên cứu sinh**: Chuyển paper PDF sang TeX để trích dẫn, chỉnh sửa công thức
- **Nhà xuất bản**: Batch convert tài liệu cũ (scan) sang TeX để tái bản
- **Thư viện**: Số hóa tài liệu riêng tư mà không upload lên cloud
- **Giảng viên**: Trích xuất đề thi/bài giảng từ PDF sang LaTeX

---

## 🚀 Quick Start

### Cài đặt

```bash
# 1. Clone repository
git clone https://github.com/phucdhh/HeySeen.git
cd HeySeen

# 2. Cài đặt dependencies
brew install poppler tesseract
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Khởi động HeySeen
./start.sh
```

Truy cập: http://localhost:5555

### Sử dụng CLI

```bash
# Chuyển đổi PDF → TeX
heyseen convert input.pdf --output output_folder

# Với Math OCR
heyseen convert paper.pdf --output result/ --math-ocr

# Xem chi tiết
heyseen convert --help
```

### Sử dụng Web Interface

1. Mở trình duyệt: http://localhost:5555
2. Upload file PDF
3. Chọn tùy chọn (Math OCR, Layout Analysis)
4. Nhấn "Convert"
5. Tải về kết quả (ZIP chứa TeX + images)

### Quản lý Service

```bash
./start.sh     # Khởi động HeySeen
./stop.sh      # Dừng HeySeen
./status.sh    # Kiểm tra trạng thái
./restart.sh   # Khởi động lại
```

---

## 📂 Kết quả Output

```
output/
├── main.tex          # File LaTeX chính
├── images/           # Hình ảnh được trích xuất
│   ├── page_01_fig_01.png
│   └── page_03_table_01.png
└── meta.json         # Metadata (block info, bounding boxes)
```

Compile LaTeX:
```bash
cd output && pdflatex main.tex
```

---

## 🎯 So sánh với Mathpix

| Tiêu chí | HeySeen | Mathpix |
|----------|---------|---------|
| **Offline & Bảo mật** | ✅ Hoàn toàn offline | ❌ Cần internet |
| **Chi phí** | ✅ Miễn phí | ❌ $4.99+/tháng |
| **Độ chính xác** | ⚠️ 75-90% | ✅ 90-95% |
| **Platform** | 🍎 macOS (Apple Silicon) | 🌐 Cross-platform |
| **Tùy biến** | ✅ Open source | ❌ Closed |
| **Batch processing** | ✅ Unlimited | ❌ Giới hạn quota |

**Kết luận**: HeySeen phù hợp cho **offline + privacy + bulk processing**, Mathpix tốt hơn về **độ chính xác và UX**.

---

## 🛠️ Production Deployment

### Auto-start Services

HeySeen tự động khởi động khi login (via `launchd`):

```bash
# Cài đặt auto-start
./deploy/install_autostart.sh

# Kiểm tra
launchctl list | grep heyseen
```

### Monitoring

- **Backend Log**: `tail -f server_data/server.log`
- **Local URL**: http://localhost:5555
- **Public URL**: https://heyseen.truyenthong.edu.vn (nếu có setup Cloudflare Tunnel)

Xem chi tiết: `./deploy/health_check.sh`

---

## 📚 Documentation

- **[TECHNICAL.md](TECHNICAL.md)** - Kiến trúc, benchmark, troubleshooting chi tiết
- **[PLAN.md](PLAN.md)** - Roadmap và development plan
- **[API.md](API.md)** - API documentation
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Hướng dẫn đóng góp

---

## 🤝 Contributing

Dự án đang ở giai đoạn đầu. Nếu quan tâm:
1. **Issues**: Report bugs hoặc đề xuất features qua GitHub Issues.
2. **Pull Requests**: Chào đón PR cho bug fixes, optimization, hoặc documentation.
3. **Testing**: Cần volunteers test với các loại PDF khác nhau (textbook, paper, thesis).

Xem chi tiết triển khai tại [PLAN.md](PLAN.md).





Contributions are welcome! Xem [CONTRIBUTING.md](CONTRIBUTING.md) để biết chi tiết.

- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/phucdhh/HeySeen/issues)
- 💡 **Feature Requests**: [GitHub Discussions](https://github.com/phucdhh/HeySeen/discussions)
- 🔧 **Pull Requests**: Fork → Branch → PR

---

## 📄 License

MIT License - xem [LICENSE](LICENSE) để biết chi tiết.

---

## 🙏 Credits

HeySeen sử dụng các công nghệ mã nguồn mở:
- [Marker](https://github.com/datalab-to/marker) - PDF to Markdown
- [Surya OCR](https://github.com/VikParuchuri/surya) - Layout Analysis
- [Texify](https://github.com/VikParuchuri/texify) - Math Recognition
- [PyTorch](https://pytorch.org/) - Deep Learning Framework

---

**Made with ❤️ for the academic community**