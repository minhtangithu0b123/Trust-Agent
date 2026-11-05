# Legal Data Crawler & Cleaner - Module Cào & Làm Sạch Dữ Liệu Pháp Luật

Hệ thống chuyên biệt phục vụ nạp, cào tự động và làm sạch (data cleaning) dữ liệu văn bản pháp luật Việt Nam (Luật, Nghị định, Thông tư, Văn bản hợp nhất). Hệ thống được thiết kế để xử lý dữ liệu thô từ nhiều nguồn khác nhau, tự động loại bỏ các thành phần rác (quảng cáo, thanh điều hướng, script) và chuyển đổi các bảng biểu phức tạp thành định dạng văn bản có ngữ cảnh (narrative format).

---

## 🌟 Tính Năng Cốt Lõi (Core Features)

### 1. 🌐 3 Phương Thức Cào & Nạp Dữ Liệu (Multi-source Data Ingestion)
- **Cào tự động qua URL**: Đọc danh sách liên kết từ `data/raw/urls.json`.
  - Hỗ trợ cào nhanh qua `requests` cho các trang web thông thường.
  - Tự động chuyển sang **Playwright Stealth** khi gặp tường lửa Cloudflare hoặc Captcha, mở trình duyệt tự động để chờ vượt tường lửa và tải toàn văn văn bản.
- **Bóc tách file PDF**: Đọc file `.pdf` từ `data/raw/`, tự động trích xuất văn bản và bóc tách bảng biểu bằng `pdfplumber` (tự động fallback sang `pypdf` nếu không có bảng).
- **Nạp file địa phương**: Tải và xử lý các file văn bản thô `.html` hoặc `.txt` lưu trực tiếp trong thư mục `data/raw/`.

---

### 2. 🧹 Module Làm Sạch & Trích Xuất Dữ Liệu (Data Cleaning & Extraction Engine)
Module làm sạch tích hợp sẵn trong [`src/loader.py`](file:///c:/Users/LENOVO/Downloads/legal-rag-chatbot/src/loader.py) thực hiện các bước chuẩn hóa tự động:
- **Khoanh vùng nội dung chính (Target Container Isolation)**:
  - Loại bỏ hoàn toàn các thẻ HTML rác: `<script>`, `<style>`, `<header>`, `<footer>`, `<nav>`, `<iframe>`, `<aside>`.
  - Cô lập chuẩn xác khung nội dung bài luật chính (`#divContent`, `#divContentText`, `.content1`, v.v.) để loại bỏ 100% menu, quảng cáo và chân trang web.
- **Chuyển đổi Bảng biểu thành Ngữ cảnh (Table Matrix to Narrative)**:
  - Bóc tách các thẻ `<table>` HTML hoặc các bảng định dạng bằng dấu phân cách `|` trong file `.txt`.
  - Tự động gắn Tên Cột (Header) tương ứng cho từng ô dữ liệu để giữ nguyên ngữ cảnh hàng-cột, tránh mất thông tin khi đưa vào xử lý ngôn ngữ tự nhiên.
- **Bóc tách Số Hiệu Văn Bản (Metadata Extraction)**:
  - Sử dụng biểu thức chính quy (Regex) phân tích 40 dòng đầu tiên và tên file để trích xuất tự động Số hiệu văn bản (Ví dụ: `36/2024/QH15`, `168/2024/NĐ-CP`, `35/2024/TT-BGTVT`).

---

## 📁 Cấu Trúc Dự Án (Project Structure)

```
legal-rag-chatbot/
│
├── data/
│   └── raw/                           # Thư mục lưu dữ liệu thô (.pdf, .html, .txt) & urls.json
│       ├── urls.json                  # Danh sách đường dẫn URL các trang văn bản luật cần cào
│       ├── luat_36_2024_qh15.html
│       ├── nghi_dinh_168_2024.html
│       ├── nghi_dinh_238_2026.html
│       ├── thong_tu_35_2024.html
│       ├── vbhn_12_2023.html
│       └── 35-2024-qh15.pdf
│
├── src/
│   ├── __init__.py
│   └── loader.py                      # Module Cào, Nạp & Làm Sạch Dữ Liệu (DocumentLoader)
│
├── requirements.txt                   # Danh sách các thư viện phụ thuộc
├── AGENTS.md                          # Quy tắc quản lý dự án
└── README.md                          # Tài liệu hướng dẫn chi tiết
```

---

## ⚙️ Cấu Trúc Dữ Liệu Đầu Ra (Output Data Schema)

Sau khi qua trình nạp và làm sạch (`DocumentLoader.load_documents()`), mỗi văn bản luật trả về một đối tượng Python `dict` chuẩn hóa có cấu trúc:

```json
{
  "source_type": "url | file",
  "source": "https://... hoặc file://data/raw/...",
  "filename": "Tên file hoặc URL",
  "so_hieu": "36/2024/QH15",
  "ten_van_ban": "Luật Trật tự, an toàn giao thông đường bộ 2024",
  "ngay_ban_hanh": "27/06/2024",
  "raw_content": "Toàn văn nội dung bài luật đã được làm sạchHTML tags, loại bỏ quảng cáo và chuyển đổi bảng biểu..."
}
```

---

## 🚀 Hướng Dẫn Nhanh (Quick Start)

### 1. Cài đặt môi trường
Đảm bảo đã cài đặt Python >= 3.10, sau đó chạy các lệnh:
```bash
# Cài đặt các thư viện Python
pip install -r requirements.txt

# Cài đặt Chromium cho Playwright (dùng khi cào qua Cloudflare)
playwright install chromium
```

### 2. Cấu hình danh sách URL cào
Cấu hình các đường dẫn văn bản luật muốn cào trong `data/raw/urls.json`:
```json
[
  {
    "url": "https://thuvienphapluat.vn/van-ban/Giao-thong-Van-tai/Luat-trat-tu-an-toan-giao-thong-duong-bo-2024-so-36-2024-QH15-444251.aspx",
    "title": "TRẬT TỰ, AN TOÀN GIAO THÔNG ĐƯỜNG BỘ",
    "notes": "Trang Thư Viện Pháp Luật"
  }
]
```

### 3. Thực thi Module Nạp & Làm Sạch Dữ Liệu
Chạy trực tiếp module:
```bash
python src/loader.py
```

### 4. Tích hợp module vào Code Python khác
```python
from src.loader import DocumentLoader

# Khởi tạo loader trỏ tới thư mục dữ liệu thô
loader = DocumentLoader(raw_dir="data/raw")

# Tiến hành cào, nạp và làm sạch toàn bộ văn bản
documents = loader.load_documents()

print(f"Đã cào & làm sạch thành công {len(documents)} văn bản luật.")
for doc in documents:
    print(f"- Số hiệu: {doc['so_hieu']} | Tiêu đề: {doc['ten_van_ban']}")
```
