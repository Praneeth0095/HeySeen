# 🔧 HeySeen - Technical Documentation

Tài liệu kỹ thuật chi tiết về kiến trúc, công nghệ và triển khai HeySeen.

---

## 📐 Kiến trúc Pipeline

HeySeen sử dụng pipeline xử lý nhiều bước:

```
PDF Input
    ↓
PDF Parsing (tách trang, render ảnh)
    ↓
Layout Analysis (Surya OCR)
    ├── Text blocks
    ├── Math blocks
    ├── Figures
    └── Tables
    ↓
Content Extraction
    ├── Text OCR (Tesseract/Marker)
    ├── Math OCR (Texify)
    └── Image Extraction
    ↓
TeX Reconstruction
    ├── main.tex
    ├── images/
    └── meta.json
```

### Các thành phần chính:

1. **PDF Loader** (`heyseen/core/pdf_loader.py`)
   - Tách trang PDF thành hình ảnh
   - Sử dụng `pdf2image` với Poppler backend
   - Hỗ trợ batch processing

2. **Layout Analyzer** (`heyseen/core/layout_analyzer.py`)
   - Phát hiện và phân loại block (text, math, figure, table)
   - Sử dụng Surya OCR layout detection
   - Xác định reading order cho đúng thứ tự

3. **Content Extractor** (`heyseen/core/content_extractor.py`)
   - Text extraction với Marker/Tesseract
   - Math recognition với Texify
   - Table recognition

4. **TeX Builder** (`heyseen/core/tex_builder.py`)
   - Tái dựng document structure
   - Generate LaTeX code
   - Link figures và equations

---

## 💻 Yêu cầu Kỹ thuật

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Processor | Apple M1 | Apple M2 Pro/Max/Ultra |
| RAM | 16 GB | 32 GB |
| Storage | 10 GB free | 50 GB free (for models & cache) |
| OS | macOS 13 Ventura | macOS 14 Sonoma+ |

### Software Dependencies

#### System Packages
```bash
brew install poppler      # PDF rendering
brew install tesseract    # OCR fallback
```

#### Python Environment
- Python 3.10 hoặc mới hơn
- Virtual environment (khuyến nghị `venv`)

#### Core Libraries
```bash
# PyTorch with MPS (Metal Performance Shaders) support
pip install --pre torch torchvision torchaudio \
    --extra-index-url https://download.pytorch.org/whl/nightly/cpu

# OCR & Document Processing
pip install marker-pdf surya-ocr texify

# Web Server (optional)
pip install fastapi uvicorn

# See requirements.txt for full list
```

---

## 📊 Performance Benchmarks

### Throughput (M2 Pro, 16GB RAM)

| Model/Step | Throughput | Memory Usage |
|-----------|-----------|--------------|
| **Surya Layout** | 2-3 pages/sec | ~4 GB |
| **Texify Math OCR** | 1-2 formulas/sec | ~3 GB |
| **Text OCR** | 10+ pages/sec | ~1 GB |
| **Full Pipeline** | **0.5-1 page/sec** | **8-10 GB** |

### Accuracy (Estimated on Academic Papers)

| Task | Accuracy | Notes |
|------|----------|-------|
| **Layout Detection** | 85-90% | Block classification |
| **Text OCR** | 90-95% | Clean printed text |
| **Math OCR** | 75-85% | LaTeX formula match |
| **Reading Order** | 80-90% | Multi-column layouts |

*Lưu ý: Số liệu ước tính dựa trên tài liệu học thuật tiêu chuẩn (2-column, moderate math). Actual performance phụ thuộc vào độ phức tạp.*

### Optimization Tips

1. **Batch Processing**: Xử lý nhiều trang cùng lúc để tận dụng GPU
2. **Caching**: Lưu kết quả trung gian để tránh rerun
3. **MPS Acceleration**: Luôn enable Metal Performance Shaders:
   ```bash
   export PYTORCH_ENABLE_MPS_FALLBACK=1
   ```
4. **Memory Management**: Giải phóng cache sau mỗi batch:
   ```python
   torch.mps.empty_cache()
   ```

---

## 🚧 Hạn chế Kỹ thuật

### Known Limitations

1. **Chữ viết tay (Handwriting)**
   - Các model hiện tại (Marker/Surya) được train chủ yếu trên chữ in
   - Độ chính xác giảm đáng kể với handwritten notes
   - Mathpix vượt trội hơn trong trường hợp này

2. **Layout phức tạp**
   - Sách giáo khoa với nhiều cột lồng nhau
   - Text bao quanh hình ảnh (text wrapping)
   - Sidebar và footnotes có thể bị sai thứ tự

3. **Math Symbols**
   - Ký hiệu toán học hiếm gặp có thể bị nhận dạng sai
   - Font toán học custom cần training thêm
   - Matrix lớn và phức tạp có accuracy thấp hơn

4. **RAM Usage**
   - Chạy model Surya + Texify song song có thể dùng >10GB RAM
   - Cần quản lý memory manually trên máy 16GB
   - Swap có thể ảnh hưởng performance nghiêm trọng

5. **Language Support**
   - Hiện tại tối ưu cho English và các ngôn ngữ Latin
   - CJK (Chinese, Japanese, Korean) cần model riêng
   - Mixed-language documents có thể có vấn đề

---

## 🔧 Nguồn Công nghệ

### Core Technologies

1. **Marker** - https://github.com/datalab-to/marker
   - PDF to Markdown converter
   - Text extraction pipeline
   - License: Apache 2.0

2. **Surya OCR** - https://github.com/VikParuchuri/surya
   - Layout analysis
   - Reading order detection
   - Multilingual text detection

3. **Texify** - https://github.com/VikParuchuri/texify
   - Math formula recognition
   - LaTeX generation
   - Fine-tuned on academic papers

4. **PyTorch**
   - Deep learning framework
   - MPS (Metal) backend for Apple Silicon
   - Model inference

### Additional Libraries

- **pdf2image**: PDF → Image conversion
- **Pillow**: Image processing
- **FastAPI**: Web API framework
- **Uvicorn**: ASGI server

---

## 🔍 FAQ & Troubleshooting

### General Questions

**Q: Tại sao không dùng Tesseract trực tiếp?**  
A: Tesseract là OCR engine tốt cho text thuần túy, nhưng yếu ở:
- Layout phức tạp (multi-column)
- Math formula recognition
- Reading order detection

HeySeen dùng Surya (layout) + Texify (math) cho độ chính xác cao hơn.

**Q: RAM 16GB có đủ không?**  
A: Đủ cho xử lý tuần tự (1 page hoặc nhỏ batch). Nếu muốn:
- Batch lớn (>5 pages): cần 32GB
- Process multiple PDFs đồng thời: cần 32GB+
- Xem metric trong `status.sh` để monitor

**Q: MPS (Metal) có nhanh hơn CPU?**  
A: Có, thường nhanh gấp 2-3 lần trên M-series chips:
- M1: ~2x speedup
- M2/M3: ~2.5-3x speedup
- Dùng `PYTORCH_ENABLE_MPS_FALLBACK=1` để tránh crash với ops chưa support

**Q: Làm sao biết pipeline đang chạy đúng?**  
A: Kiểm tra output:
```bash
# Xem meta.json
cat output/meta.json | jq '.pages[0].blocks[0]'

# Check for block_types và bbox
if [ -f "output/meta.json" ]; then
    echo "✓ Layout analysis hoạt động"
fi
```

### Common Issues

**Issue: "OSError: cannot open resource"**
```bash
# Solution: Cài đặt poppler
brew install poppler
```

**Issue: "Killed" during processing**
```bash
# Out of memory - giảm batch size hoặc tăng RAM
# Trong heyseen/core/layout_analyzer.py:
BATCH_SIZE = 1  # Thay vì 4-8
```

**Issue: Tunnel Error 1033**
```bash
# Restart Cloudflare Tunnel
./restart.sh
# Hoặc chỉ restart tunnel:
cd deploy && ./start_tunnel_bg.sh
```

**Issue: "ModuleNotFoundError" khi chạy**
```bash
# Đảm bảo đã activate virtual environment
source .venv/bin/activate
pip install -r requirements.txt
```

**Issue: Slow inference trên M1/M2**
```bash
# Enable MPS acceleration
export PYTORCH_ENABLE_MPS_FALLBACK=1

# Verify MPS available
python -c "import torch; print(torch.backends.mps.is_available())"
```

---

## 🧪 Testing & Quality Assurance

### Running Tests

```bash
# Activate environment
source .venv/bin/activate

# Run all tests
pytest tests/

# Run specific test suites
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests

# With coverage
pytest --cov=heyseen tests/
```

### Quality Metrics

Đánh giá chất lượng output:

1. **Text Accuracy (WER - Word Error Rate)**
   ```bash
   python scripts/compare_results.py --original test.tex --output output/main.tex
   ```

2. **LaTeX Validity**
   ```bash
   cd output && pdflatex main.tex
   # Check for compilation errors
   ```

3. **Layout Fidelity**
   - So sánh visual với PDF gốc
   - Kiểm tra reading order
   - Verify figure placement

---

## 🗺️ Development Roadmap

### Phase 1 — Pipeline MVP ✅
- [x] PDF → TeX conversion working
- [x] Layout analysis integration
- [x] Math OCR functional
- [x] CLI interface
- [x] Web interface

### Phase 2 — Quality & UX (In Progress)
- [ ] Diff viewer (compare PDF vs generated TeX)
- [ ] Interactive correction UI
- [ ] Batch processing optimization
- [ ] Progress tracking

### Phase 3 — Advanced Features
- [ ] Multi-document processing
- [ ] Custom templates
- [ ] Export to other formats (Markdown, Word)
- [ ] Plugin system
- [ ] Cloud deployment option

### Phase 4 — Production Ready
- [ ] CI/CD pipeline
- [ ] Automated testing
- [ ] Performance monitoring
- [ ] User analytics
- [ ] Documentation site

---

## 📚 Additional Resources

- **Architecture Diagrams**: See `docs/architecture/`
- **API Documentation**: See [API.md](API.md)
- **Development Plan**: See [PLAN.md](PLAN.md)
- **Comparison Reports**: See `docs/reports/`

---

## 📝 License & Attribution

HeySeen is licensed under MIT License. See [LICENSE](LICENSE) for details.

### Third-party Credits

- Marker by Datalab
- Surya OCR by Vik Paruchuri
- Texify by Vik Paruchuri
- PyTorch by Meta AI

---

**For non-technical documentation, see [README.md](README.md)**
