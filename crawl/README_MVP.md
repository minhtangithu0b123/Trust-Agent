# Trust Agent — Labor Agent / RAG MVP

MVP này chỉ phục vụ tra cứu semantic retrieval cho dữ liệu Luật Lao động Việt Nam. Chưa triển khai multi-agent, router, frontend, LangGraph, blockchain, payment hoặc LLM sinh câu trả lời.

## Dữ liệu thực tế và assumption

Workspace hiện không có `legal_documents.json`. Dataset được dùng là `data/raw/lao_dong.json`, gồm 1.108 bản ghi với các trường:

```text
source, so_hieu, ten_van_ban, chuong, dieu, tieu_de_dieu, khoan, text
```

Dữ liệu có dấu hiệu mojibake UTF-8 nhiều lớp. Pipeline dùng `ftfy` để sửa text trước khi tạo embedding. Vì mỗi record đã đại diện cho Điều/Khoản và chỉ có hai record dài hơn 2.000 ký tự, MVP không cắt mù quáng; mỗi record được ingest thành một document giữ nguyên cấu trúc hiện có.

`effective_from` chưa tồn tại trong input nên metadata Chroma lưu chuỗi rỗng `""`, rồi API có thể diễn giải thành null. Đây là giới hạn của metadata Chroma, vốn không nhận `None` ổn định ở mọi phiên bản.

## Cài đặt

Yêu cầu Python 3.11.

```powershell
cd D:\Trust-AGENT\crawl
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
Copy-Item .env.example .env
```

Embedding mặc định là `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`: model local, miễn phí, hỗ trợ nhiều ngôn ngữ và phù hợp baseline tiếng Việt. Lần chạy đầu sẽ tải model từ Hugging Face; các lần sau dùng cache local. Không cần API key.

## Ingest vào ChromaDB persistent

```powershell
python scripts\ingest_labor.py
```

Chroma được lưu tại `data/chroma/`, collection là `legal_labor`. Lệnh ingest có tính idempotent theo `id` hash; chạy lại sẽ bỏ qua document đã có thay vì thêm bản sao.

Metadata mỗi document gồm:

```text
id, domain, so_hieu, ten_van_ban, chuong, dieu, khoan,
source, effective_from, status
```

## Chạy API

```powershell
python -m uvicorn app.main:app --reload
```

Endpoints:

```text
GET  http://127.0.0.1:8000/health
POST http://127.0.0.1:8000/ingest
POST http://127.0.0.1:8000/search
```

Ví dụ PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod -Method Post http://127.0.0.1:8000/ingest
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/search `
  -ContentType 'application/json' `
  -Body '{"query":"Người lao động có quyền đơn phương chấm dứt hợp đồng khi nào?","k":5}'
```

Response search có `content`, metadata đầy đủ và citation gồm tên văn bản, số hiệu, Điều, Khoản và source. Đây là retrieval + citation; chưa có bước LLM trả lời.

## Test

```powershell
python -m pytest -q
python scripts\test_retrieval.py
```

`test_retrieval.py` chạy ba câu hỏi tiếng Việt về chấm dứt hợp đồng, thời giờ làm việc và tiền lương. Script yêu cầu đã ingest và model embedding đã được tải.

## Cấu trúc

```text
app/
  config.py          # Settings từ .env
  normalization.py   # đọc, sửa encoding, chuẩn hóa record
  vectorstore.py     # embedding, Chroma persistent, ingest/search
  main.py            # FastAPI
scripts/
  ingest_labor.py
  test_retrieval.py
tests/
data/raw/lao_dong.json
data/chroma/          # sinh sau ingest, không commit
```

## Giới hạn MVP

- Chưa đánh giá factual accuracy bằng bộ gold labels.
- Chưa có temporal validity filtering đầy đủ hoặc effective date extraction.
- Chưa có OCR cho PDF scan.
- Chưa crawl URL trong API; dữ liệu MVP lấy từ JSON Lao động đã có.
- Không hard-code API key và không có LLM generation.

## Milestone 2 — Hybrid Retrieval

Hybrid search kết hợp dense semantic retrieval từ ChromaDB với BM25 keyword retrieval trên chính collection `legal_labor`, sau đó hợp nhất thứ hạng bằng Reciprocal Rank Fusion (RRF). BM25 được xây từ documents hiện có trong Chroma, nên không tạo corpus thứ hai. `HybridRetriever.refresh_if_needed()` so sánh collection count; nếu `/ingest` thêm dữ liệu, index BM25 sẽ tự refresh ở lần search sau.

```powershell
python scripts\ingest_labor.py
python -m uvicorn app.main:app --reload
```

Gọi endpoint:

```powershell
$body = @{ query = 'Người lao động có quyền đơn phương chấm dứt hợp đồng khi nào?'; k = 5 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/search/hybrid -ContentType 'application/json' -Body $body
```

Response có `strategy: "hybrid_rrf"`, `text`, `fused_score`, metadata và citation gồm tên văn bản, số hiệu, chương, Điều, khoản, source.

Chạy evaluation 10 câu hỏi:

```powershell
python scripts\evaluate_retrieval.py
```

Báo cáo được ghi tại `reports/retrieval_evaluation.json` với query, expected Điều, top-k returned và pass/fail.
## Milestone 3 — Grounded Answer Generator và Citation Verifier

Milestone này thêm `POST /ask` nhưng vẫn giữ semantic search, hybrid search và các endpoint cũ. Luồng là hybrid retrieval → evidence top-k → legal context → LLM provider → verifier.

### Cấu hình provider

Tạo file `.env` từ `.env.example`, sau đó điền khóa của bạn trên máy local:

```powershell
Copy-Item .env.example .env
# sửa OPENAI_API_KEY trong .env
OPENAI_MODEL=gpt-4o-mini
```

Không commit `.env`. Nếu thiếu `OPENAI_API_KEY`, `/ask` không làm server crash mà trả `status: "provider_error"`. Test dùng mock provider và không gọi OpenAI thật.

Cài dependency sau khi pull code:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

### Gọi `/ask`

```powershell
$body = @{ query = 'Thời giờ làm việc bình thường của người lao động là bao nhiêu?'; k = 5 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/ask `
  -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

Response rút gọn:

```json
{
  "query": "...",
  "answer": "...",
  "status": "verified",
  "citations": [{
    "document_id": "...",
    "so_hieu": "45/2019/QH14",
    "ten_van_ban": "Bộ luật Lao động 2019",
    "chuong": "...",
    "dieu": "Điều ...",
    "khoan": "Khoản ...",
    "source": "...",
    "status": "unknown",
    "effective_from": null
  }],
  "evidence": [{"document_id": "...", "text": "...", "fused_score": 0.03, "metadata": {}}],
  "retrieval_strategy": "hybrid_rrf"
}
```

LLM chỉ được trả về `cited_document_ids`. Citation cuối cùng được tạo từ metadata của evidence thật, không lấy tự do từ câu trả lời. Nếu LLM đưa ID không có trong evidence, hoặc không có evidence, verifier trả `insufficient_evidence` và câu: `Chưa đủ căn cứ từ dữ liệu hiện có để kết luận.`

### Test và smoke evaluation

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\evaluate_ask.py
```

Script chạy 5 câu hỏi Lao động với mock provider, kiểm tra retrieval và citation verifier. Nếu đã có `.env` hợp lệ, chạy API rồi gọi `/ask` để kiểm thử provider thật. Hệ thống hiện chưa có multi-agent, LangGraph, frontend, memory, Router, temporal validation đầy đủ hoặc cơ chế thay thế tư vấn pháp lý chuyên nghiệp.

## Shared multi-domain foundation

Code dùng chung cho ba domain trong app/domains.py, không có ba codebase riêng:

| Domain | Corpus hiện tại | Chroma collection | Prompt |
|---|---|---|---|
| labor | data/raw/lao_dong.json | legal_labor | legal_labor_agent |
| accounting | data/raw/thue.json (assumption: corpus thuế/kế toán hiện có) | legal_accounting | legal_accounting_agent |
| traffic | data/raw/giao thông.json | legal_traffic | legal_traffic_agent |

Mỗi record được chuẩn hóa với domain, sau đó semantic search và BM25 đều lọc đúng metadata.domain. BM25 index được xây riêng theo từng collection/domain.

### Ingest domain

Labor vẫn dùng lệnh cũ:

    .\.venv\Scripts\python.exe scripts\ingest_labor.py

Hoặc dùng script generic:

    .\.venv\Scripts\python.exe scripts\ingest_domain.py labor
    .\.venv\Scripts\python.exe scripts\ingest_domain.py accounting
    .\.venv\Scripts\python.exe scripts\ingest_domain.py traffic

Nếu corpus không tồn tại, ingest trả lỗi rõ ràng và không tạo dữ liệu giả. Thêm domain mới bằng cách thêm một DomainConfig vào app/domains.py với name, collection_name, data_path, prompt_name và metadata_defaults; không cần copy normalization, Chroma, BM25, RRF hoặc citation logic.

### Domain-aware endpoints

    POST /domains/{domain}/ingest
    GET  /domains/{domain}/health
    POST /domains/{domain}/search
    POST /domains/{domain}/search/hybrid
    POST /domains/{domain}/ask

Ví dụ:

    $body = @{ query = 'Mức phạt giao thông là gì?'; k = 5 } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/domains/traffic/search/hybrid -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))

Các endpoint Labor cũ /health, /ingest, /search, /search/hybrid, /ask vẫn được giữ để backward compatible.
