# Kế hoạch build project Legal Data Crawler & Cleaner

## 1. Mục tiêu

Xây dựng một pipeline Python có thể:

1. Nạp văn bản pháp luật từ file HTML, PDF, TXT và URL.
2. Làm sạch nội dung, loại bỏ phần giao diện/rác của website.
3. Trích xuất metadata pháp lý và giữ được ngữ cảnh điều, khoản.
4. Chuẩn hóa dữ liệu về một schema thống nhất.
5. Tách và xuất dữ liệu theo lĩnh vực: giao thông, thuế/kế toán và lao động.
6. Có kiểm tra tự động để phát hiện dữ liệu lỗi trước khi đưa vào RAG hoặc hệ thống khác.

Phạm vi hiện tại là **ingestion và data quality**. Chưa xem crawler là production-ready cho đến khi có retry, logging, test, kiểm soát thay đổi dữ liệu và cơ chế xử lý Cloudflare/Captcha rõ ràng.

## 2. Trạng thái hiện tại

### Cấu trúc hiện có

```text
crawl/
├── data/raw/
│   ├── giao thông.json
│   ├── lao_dong.json
│   ├── thue.json
│   ├── thuế + lao động.json
│   ├── urls.json
│   ├── *.html
│   └── *.pdf
├── src/
│   ├── __init__.py
│   └── loader.py
├── requirements.txt
├── README.md
└── BUILD_PLAN.md
```

### Dữ liệu JSON hiện có

Ba file đã kiểm tra đồng bộ về cấu trúc:

| File | Số bản ghi | Trạng thái |
|---|---:|---|
| `data/raw/lao_dong.json` | 1.108 | Đủ 8 trường, tất cả là chuỗi |
| `data/raw/thue.json` | 593 | Đủ 8 trường, tất cả là chuỗi |
| `data/raw/giao thông.json` | 1.852 | Đủ 8 trường, tất cả là chuỗi |

Schema hiện tại:

```json
{
  "source": "https://...",
  "so_hieu": "45/2019/QH14",
  "ten_van_ban": "Luật Lao động 2019",
  "chuong": "Chương I",
  "dieu": "Điều 1",
  "tieu_de_dieu": "Phạm vi điều chỉnh",
  "khoan": "1",
  "text": "Nội dung điều khoản..."
}
```

Lưu ý: `thue.json` hiện được tách từ nguồn có tên `Luật Kế toán 2015`. Cần xác nhận nghiệp vụ rằng nhóm này thực sự được gọi là **thuế**, hay nên đổi tên thành `ke_toan.json`.

## 3. Kiến trúc mục tiêu

```text
Input sources
    ├── HTML local
    ├── PDF local
    ├── TXT local
    └── URL
          │
          ▼
Fetcher / File Reader
          │
          ▼
Content Cleaner
  - remove script/style/navigation
  - isolate legal content
  - normalize whitespace
          │
          ▼
Structure Parser
  - chapter / article / clause
  - table to narrative
  - legal document number
          │
          ▼
Schema Normalizer
          │
          ├── validation report
          ├── clean JSONL/JSON
          └── dataset by domain
```

Nên tách logic hiện đang nằm trong `loader.py` thành các module nhỏ khi bắt đầu build thật:

```text
src/
├── __init__.py
├── config.py              # đường dẫn, timeout, user-agent, chế độ browser
├── models.py              # schema DocumentRecord
├── readers.py             # HTML/PDF/TXT reader
├── fetchers.py            # requests và Playwright
├── cleaners.py            # làm sạch HTML/text/table
├── metadata.py            # trích số hiệu, tên, ngày ban hành
├── normalizer.py          # chuẩn hóa bản ghi đầu ra
├── validator.py           # kiểm tra schema và chất lượng dữ liệu
├── pipeline.py            # điều phối toàn bộ quy trình
└── cli.py                 # lệnh command-line
```

Có thể giữ `loader.py` làm facade tương thích trong giai đoạn chuyển đổi để code cũ không bị hỏng.

## 4. Các giai đoạn cần thực hiện

### Giai đoạn 0 — Chốt phạm vi và dữ liệu chuẩn

- [ ] Xác nhận domain chính thức: `giao_thong`, `thue` và `lao_dong`.
- [ ] Xác nhận `thue.json` có phải dữ liệu thuế hay thực chất là kế toán.
- [ ] Quy định tên file không dấu, dùng `snake_case`.
- [ ] Quy định encoding UTF-8 cho toàn bộ source và output.
- [ ] Quy định file gốc trong `data/raw/` là immutable; output phải ghi sang thư mục riêng.
- [ ] Quy định một bản ghi tương ứng với một điều/khoản hoặc một đoạn pháp lý có thể truy xuất.

### Giai đoạn 1 — Sửa nền tảng project

- [ ] Sửa lỗi hiển thị tiếng Việt bị mojibake trong `README.md` và `src/loader.py` nếu đó là lỗi encoding thật, không chỉ do terminal.
- [ ] Cập nhật README để khớp repository hiện tại; loại bỏ các đường dẫn cũ như `file:///c:/Users/...`.
- [ ] Thêm `.venv/`, cache, log và output sinh tự động vào `.gitignore`.
- [ ] Tạo `pyproject.toml` hoặc tối thiểu một script setup có version Python hỗ trợ.
- [ ] Pin phiên bản dependency quan trọng sau khi kiểm tra tương thích.
- [ ] Tạo thư mục `tests/`, `data/processed/`, `reports/` và `logs/`.

### Giai đoạn 2 — Chuẩn hóa schema

Nên dùng model rõ ràng, có thể bắt đầu bằng `dataclass` hoặc Pydantic:

```python
class DocumentRecord:
    source: str
    source_type: str       # file | url
    filename: str | None
    domain: str             # giao_thong | thue | lao_dong
    so_hieu: str
    ten_van_ban: str
    ngay_ban_hanh: str | None
    chuong: str | None
    dieu: str | None
    tieu_de_dieu: str | None
    khoan: str | None
    text: str
```

Việc cần làm:

- [ ] Quyết định giữ schema 8 trường hiện tại hay nâng lên schema có `domain`, `source_type`, `filename`, `ngay_ban_hanh`.
- [ ] Viết migration từ 3 file JSON hiện tại sang schema mới.
- [ ] Không tự bịa metadata bị thiếu; dùng `null` hoặc `N/A` theo một quy ước duy nhất.
- [ ] Chuẩn hóa khoảng trắng, xuống dòng, Unicode và ký tự HTML còn sót.
- [ ] Bảo toàn `source` để có thể truy ngược bản ghi về tài liệu gốc.

### Giai đoạn 3 — Tách reader và cleaner

- [ ] Tách đọc HTML, PDF và TXT thành các hàm độc lập.
- [ ] Với HTML, xóa `script`, `style`, `header`, `footer`, `nav`, `iframe`, `aside`.
- [ ] Ưu tiên các container pháp lý đã biết như `#divContent`, `#divContentText`, `.content1`.
- [ ] Nếu không tìm thấy container, ghi cảnh báo và lưu lý do fallback.
- [ ] Với PDF, thử `pdfplumber`, fallback sang `pypdf` khi cần.
- [ ] Kiểm tra PDF scan không có text; nếu không có OCR thì đánh dấu `needs_ocr`, không coi là đã trích xuất thành công.
- [ ] Chuyển bảng thành narrative nhưng giữ tên cột và thứ tự dòng.
- [ ] Viết test riêng cho bảng HTML, bảng PDF và bảng dạng `|` trong TXT.

### Giai đoạn 4 — Parser cấu trúc pháp luật

- [ ] Tách `Chương`, `Mục`, `Điều`, `Khoản`, `Điểm` bằng parser có regex được test trên nhiều văn bản.
- [ ] Không chỉ dựa vào 40 dòng đầu nếu văn bản có phần mở đầu dài hoặc định dạng khác.
- [ ] Trích `so_hieu` từ nội dung trước, sau đó fallback sang tên file/URL.
- [ ] Hỗ trợ các dạng như `36/2024/QH15`, `168/2024/NĐ-CP`, `35/2024/TT-BGTVT`.
- [ ] Ghi `parse_status` hoặc cảnh báo khi không tìm được số hiệu, điều hoặc khoản.
- [ ] Không gộp các điều khác nhau vào một chunk nếu không có quy tắc rõ ràng.

### Giai đoạn 5 — Ingestion URL an toàn

- [ ] Đọc URL từ `data/raw/urls.json` theo schema có `url`, `title`, `notes`.
- [ ] Thêm timeout, retry có backoff và giới hạn số lần thử.
- [ ] Ghi HTTP status, thời gian phản hồi và lỗi vào log.
- [ ] Dùng `requests` cho trang thường.
- [ ] Chỉ dùng Playwright khi requests không lấy được nội dung hoặc gặp trang chống bot.
- [ ] Không coi việc mở được trình duyệt là crawl thành công; phải kiểm tra nội dung pháp luật có độ dài tối thiểu.
- [ ] Tách profile trình duyệt tạm thời, không commit `browser_user_data`.
- [ ] Cân nhắc điều khoản sử dụng, robots.txt và giới hạn tốc độ trước khi crawl số lượng lớn.

### Giai đoạn 6 — Dataset processing

- [ ] Giữ nguyên `data/raw/` làm dữ liệu nguồn.
- [ ] Ghi output vào `data/processed/`:

```text
data/processed/
├── giao_thong.jsonl
├── thue.jsonl
├── lao_dong.jsonl
├── all_documents.jsonl
└── manifest.json
```

- [ ] Tạo `manifest.json` gồm thời gian chạy, số bản ghi, hash file input, số lỗi và cảnh báo.
- [ ] Dùng JSONL cho pipeline lớn; chỉ xuất JSON array khi cần giao tiếp với ứng dụng khác.
- [ ] Deduplicate theo tổ hợp `source + so_hieu + dieu + khoan + text_hash`.
- [ ] Báo cáo các bản ghi trùng, text rỗng, text quá ngắn và metadata `N/A`.
- [ ] Không xóa dữ liệu nguồn hoặc ghi đè output cũ; tạo run directory hoặc backup.

### Giai đoạn 7 — Validation và test

Tối thiểu cần có:

- [ ] Unit test cho `extract_so_hieu`.
- [ ] Unit test cho chuyển bảng sang narrative.
- [ ] Unit test cho HTML cleaner.
- [ ] Test parser trên ít nhất một file HTML, PDF và URL fixture.
- [ ] Test schema: đủ trường, đúng kiểu, không có field thừa.
- [ ] Test encoding: tiếng Việt đọc/ghi UTF-8 không bị biến thành `Ã`, `Ä`, `â`.
- [ ] Test smoke toàn pipeline trên một tài liệu nhỏ trước khi chạy toàn bộ.
- [ ] Test idempotency: chạy hai lần không tạo bản ghi trùng ngoài dự kiến.

Các chỉ số cần ghi trong báo cáo:

```text
input_files
documents_loaded
records_emitted
records_dropped
empty_text_records
missing_so_hieu
duplicate_records
fetch_failures
parse_warnings
```

### Giai đoạn 8 — CLI và vận hành

Đề xuất các lệnh:

```powershell
# Kiểm tra môi trường
python -m src.cli doctor

# Chạy thử một file
python -m src.cli run --input data/raw/luat_36_2024_qh15.html --output data/processed/smoke.jsonl

# Validate ba dataset hiện có
python -m src.cli validate --input data/raw

# Chạy pipeline đầy đủ
python -m src.cli run --input data/raw --output data/processed

# Chỉ crawl URL
python -m src.cli crawl --urls data/raw/urls.json --output data/processed
```

CLI nên có `--dry-run`, `--limit`, `--domain`, `--headless`, `--output`, `--log-level` và mã thoát khác 0 khi validation thất bại.

## 5. Lệnh cài đặt và smoke test dự kiến

Chạy trong PowerShell:

```powershell
cd D:\Trust-AGENT\crawl
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium
python -m py_compile src\loader.py
python src\loader.py
```

Không nên chạy crawl toàn bộ ngay lần đầu. Trước tiên:

1. Chạy một file HTML local.
2. Chạy một file PDF local.
3. Validate một JSON dataset.
4. Chạy một URL với giới hạn 1 URL.
5. Kiểm tra output và log bằng mắt.
6. Sau đó mới chạy toàn bộ dữ liệu.

## 6. Tiêu chí hoàn thành MVP

MVP được coi là đạt khi:

- [ ] Có lệnh cài đặt mới từ đầu trên Windows.
- [ ] Có một lệnh chạy rõ ràng cho local files và URL.
- [ ] Ba domain dùng chung một schema và được validate tự động.
- [ ] Dữ liệu raw không bị ghi đè.
- [ ] HTML/PDF/TXT có test smoke tương ứng.
- [ ] Có báo cáo số bản ghi thành công, lỗi, thiếu metadata và trùng lặp.
- [ ] Không còn lỗi encoding tiếng Việt trong output chuẩn.
- [ ] Có README cập nhật đúng với mã nguồn thực tế.
- [ ] Có hướng dẫn xử lý Cloudflare/Captcha, nhưng không tuyên bố crawler vượt bot là luôn thành công.

## 7. Thứ tự ưu tiên đề xuất

### Ưu tiên P0 — phải làm trước

1. Chốt schema và cách gọi domain `thue`/`ke_toan`.
2. Sửa encoding và cập nhật README.
3. Tạo validator cho ba file JSON hiện có.
4. Tạo test và smoke test cho `loader.py`.
5. Tách output khỏi `data/raw/`.

### Ưu tiên P1 — để có pipeline dùng được

1. Tách reader/cleaner/parser khỏi `loader.py`.
2. Thêm CLI.
3. Thêm manifest, log, deduplication và retry.
4. Chuẩn hóa JSONL theo domain.

### Ưu tiên P2 — để tiến tới production

1. OCR cho PDF scan.
2. Queue/job cho crawl nhiều URL.
3. Database hoặc object storage cho document versions.
4. Monitoring và cảnh báo crawl thất bại.
5. Versioning dataset và regression test theo từng văn bản pháp luật.

## 8. Rủi ro cần theo dõi

- Website thay đổi DOM khiến selector container không còn đúng.
- Cloudflare/Captcha làm kết quả crawl không ổn định.
- PDF scan không có text layer.
- Regex tách điều/khoản nhầm với số hiệu hoặc số trong nội dung.
- Dữ liệu cùng một văn bản xuất hiện ở nhiều nguồn và bị trùng.
- Encoding lỗi làm hỏng tên văn bản, regex và câu trả lời tiếng Việt.
- Việc đổi tên nhóm `thue` có thể gây sai phân loại nghiệp vụ nếu thực tế đó là dữ liệu kế toán.

## 9. Kết quả bàn giao cuối cùng

Khi hoàn tất build, repository nên có tối thiểu:

```text
src/
├── cli.py
├── config.py
├── fetchers.py
├── readers.py
├── cleaners.py
├── metadata.py
├── normalizer.py
├── validator.py
└── pipeline.py
tests/
data/raw/
data/processed/
reports/
README.md
BUILD_PLAN.md
pyproject.toml
```

Bản build cuối phải được đánh giá bằng artifact và log thực tế. Việc chương trình chạy không tự động chứng minh rằng nội dung pháp luật đã được trích xuất đầy đủ hoặc chính xác; cần giữ báo cáo validation và một số mẫu để review thủ công.
