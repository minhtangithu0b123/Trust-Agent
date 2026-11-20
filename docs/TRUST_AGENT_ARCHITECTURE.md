# Trust Agent — Kiến trúc hệ thống

## 1. Mục tiêu

Trust Agent là hệ thống tra cứu pháp luật Việt Nam theo mô hình RAG. Hệ thống hiện hỗ trợ ba domain:

- `traffic`: pháp luật giao thông
- `labor`: pháp luật lao động
- `accounting`: kế toán và thuế

Hệ thống ưu tiên trả lời dựa trên dữ liệu pháp luật đã được ingest và đính kèm citation từ evidence thực tế. LLM không được dùng để tự tạo citation hoặc tự bổ sung dữ kiện ngoài evidence.

## 2. Sơ đồ tổng quát

```text
Người dùng
   │
   ▼
Next.js Frontend (web/)
   │  /api/* proxy
   ▼
FastAPI Backend (crawl/app/main.py)
   │
   ├── API tra cứu domain cũ
   │      ├── /search
   │      ├── /search/hybrid
   │      ├── /ask
   │      └── /domains/{domain}/...
   │
   ├── Router (crawl/app/router.py)
   │      ├── classify query
   │      ├── fan-out song song bằng LangGraph + Send
   │      ├── Traffic Agent
   │      ├── Labor Agent
   │      ├── Accounting Agent
   │      └── synthesize kết quả
   │
   └── Specialized ReAct Agents
          │
          ├── query normalization / expansion
          ├── search domain-specific law
          ├── get domain document
          ├── verify citation
          └── grounded answer
                 │
                 ├── ChromaDB persistent
                 ├── dense semantic retrieval
                 ├── BM25 keyword retrieval
                 └── RRF fusion
```
## 3. Frontend

Thư mục: `web/`

Frontend là ứng dụng Next.js. Browser gọi các route `/api/*` của frontend thay vì gọi trực tiếp API key hoặc LLM provider.

Luồng chính:

```text
User nhập câu hỏi
  → Next.js gửi request tới /api/ask
  → server route forward tới backend /router/ask
  → nhận answer, status, citations, evidence
  → render câu trả lời và nguồn tham khảo
```

Frontend có thể dùng biến môi trường `TRUST_AGENT_API_URL` để trỏ tới backend local, server Docker hoặc Cloudflare Tunnel. Không đặt `OPENAI_API_KEY` ở frontend/Vercel.

Các chức năng giao diện chính:

- tạo cuộc hội thoại mới;
- gửi câu hỏi;
- hiển thị câu trả lời và trạng thái căn cứ;
- hiển thị citation/source;
- tải danh sách cuộc hội thoại;
- xóa cuộc hội thoại;
- hiển thị lịch sử tra cứu.

## 4. Backend FastAPI

File trung tâm: `crawl/app/main.py`

Backend chịu trách nhiệm:

- khởi tạo FastAPI;
- khai báo request/response model;
- chuẩn hóa query trước khi xử lý;
- gọi Router hoặc domain agent;
- expose health check;
- xử lý conversation API;
- trả lỗi an toàn, không làm server crash khi provider lỗi.

### API chính

| Endpoint | Mục đích |
|---|---|
| `GET /health` | Kiểm tra backend và collection mặc định |
| `POST /search` | Semantic search cũ |
| `POST /search/hybrid` | Dense + BM25 + RRF |
| `POST /ask` | Grounded answer theo domain mặc định |
| `POST /domains/{domain}/search` | Search theo domain |
| `POST /domains/{domain}/search/hybrid` | Hybrid search theo domain |
| `POST /domains/{domain}/ask` | Answer theo domain |
| `POST /router/ask` | Router đa domain |
| `POST /agents/traffic/ask` | ReAct Traffic Agent |
| `POST /agents/labor/ask` | ReAct Labor Agent |
| `POST /agents/accounting/ask` | ReAct Accounting Agent |

Canonical domain chỉ gồm:

```text
traffic
labor
accounting
```

## 5. Query normalization

Module: `crawl/app/query_normalization.py`

Hệ thống duy trì hai biểu diễn query:

### `original_query`

- NFC Unicode;
- trim khoảng trắng đầu/cuối;
- gộp nhiều whitespace thành một khoảng trắng;
- giữ nguyên dấu tiếng Việt, số, dấu `/`, `-`, `.`, Điều/Khoản và số hiệu văn bản;
- được dùng cho retrieval, LLM, citation và response.

### `routing_query`

- lowercase/casefold;
- bỏ dấu phục vụ keyword routing;
- map `đ` thành `d`;
- chỉ dùng cho phân loại deterministic.

Ngoài ra có query expansion theo domain. Ví dụ:

```text
muc phat nong do con
→ Mức phạt nồng độ cồn ... xử phạt vi phạm nồng độ cồn
```

Query expansion chỉ bổ sung thuật ngữ tìm kiếm đã được cấu hình, không tự thêm điều luật, mức phạt hoặc citation.

## 6. Router đa domain

File: `crawl/app/router.py`

Router dùng LangGraph với graph:

```text
START
  → classify_query
  → Send fan-out song song
       ├── query_traffic
       ├── query_labor
       └── query_accounting
  → synthesize_results
  → END
```

### Phân loại

Router ưu tiên structured LLM classification khi provider sẵn sàng. Nếu LLM lỗi hoặc không có key, hệ thống dùng keyword fallback trên `routing_query`.

LLM chỉ được chọn một trong ba domain canonical. Không dùng alias `legal_traffic`, `legal_labor`, `legal_accounting` trong Router.

### Fan-out

Mỗi nhánh gọi trực tiếp hàm Python của ReAct Agent tương ứng, không gọi HTTP nội bộ và không gọi API endpoint qua network.

Kết quả parallel được gom bằng reducer `operator.add`, tránh mất output của các nhánh.

### Synthesis

- một domain verified: dùng câu trả lời domain đó;
- nhiều domain verified: tổng hợp ngắn gọn từ các câu trả lời đã verified;
- domain insufficient: phải thông báo thiếu căn cứ;
- không có domain verified: trả thông báo an toàn;
- citations được deduplicate theo `document_id`.

## 7. ReAct Agents

Các agent dùng chung vòng lặp nội bộ trong module base và chỉ thay đổi phần domain-specific.

Mỗi agent có hai tool domain-locked:

```text
search_<domain>_law(query, k)
get_<domain>_document(document_id)
```

Ví dụ Traffic Agent chỉ được truy cập collection `legal_traffic`. Model không thể truyền domain khác vào tool.

Vòng đời xử lý:

```text
query
  → agent quyết định tool
  → search evidence
  → quan sát evidence
  → có thể search lại hoặc lấy document cụ thể
  → tạo structured final answer
  → kiểm tra cited_document_ids
  → trả answer/status/citations
```

Giới hạn an toàn:

- giới hạn số bước/tool call;
- không trả chain-of-thought hoặc tool trace ra API;
- chỉ cho phép citation có trong evidence đã quan sát;
- thiếu hoặc sai citation thì không trả `verified`;
- thiếu evidence dùng trạng thái `insufficient_evidence`;
- lỗi provider dùng trạng thái `provider_error`.

## 8. Retrieval pipeline

### Domain configuration

Mỗi domain có cấu hình riêng:

| Domain | Chroma collection | Corpus |
|---|---|---|
| `labor` | `legal_labor` | dữ liệu Luật Lao động |
| `traffic` | `legal_traffic` | dữ liệu pháp luật giao thông |
| `accounting` | `legal_accounting` | dữ liệu kế toán/thuế |

### Ingest

Script ingest đọc corpus JSON, chuẩn hóa document/chunk và lưu vào ChromaDB persistent.

Metadata chuẩn gồm các trường chính:

```text
id
domain
so_hieu
ten_van_ban
chuong
dieu
khoan
source
effective_from
status
```

Ingest có tính idempotent: document đã tồn tại sẽ được bỏ qua thay vì thêm trùng.

### Hybrid retrieval

```text
Query
 ├── Dense search → ChromaDB
 └── Sparse search → BM25
          ↓
       RRF fusion
          ↓
       top-k evidence
```

RRF dùng công thức dạng:

```text
RRF_score(document) = Σ 1 / (rrf_k + rank)
```

Các truy vấn luôn bị giới hạn theo domain để tránh trộn dữ liệu giữa giao thông, lao động và kế toán.

## 9. Answering và citation verification

Module chính: `crawl/app/answering.py`

Luồng answer:

```text
query
  → hybrid retrieval
  → chọn evidence
  → build legal context/excerpt
  → LLM generation
  → parse cited_document_ids
  → deterministic citation verification
  → response
```

Prompt yêu cầu LLM:

- chỉ dùng evidence được cung cấp;
- không bịa Điều, Khoản, số tiền hoặc ngày hiệu lực;
- trả lời tiếng Việt ngắn gọn, đúng trọng tâm;
- phân biệt quy định pháp luật và suy luận theo tình huống;
- nếu thiếu căn cứ phải nói rõ.

Citation được tạo từ metadata của evidence, không lấy nguyên văn citation do LLM tự viết.

Các status quan trọng:

```text
verified
insufficient_evidence
provider_error
needs_clarification
```

Nếu answer chứa câu kết luận thiếu căn cứ thì không được đánh dấu `verified`, kể cả khi LLM trả về citation ID.

## 10. LLM provider và cấu hình

Settings được đọc tập trung qua `get_settings()`.

Các cấu hình cần có trong môi trường backend:

```env
LLM_PROVIDER=openai
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_KEY=...
```

API key chỉ đặt ở backend `.env` hoặc secret manager. Không commit `.env`, không đặt API key trong frontend và không đưa key vào file Markdown này.

Nếu provider lỗi:

1. API vẫn nên trả JSON hợp lệ.
2. Agent trả `provider_error`.
3. Router không crash server.
4. Không được tạo câu trả lời pháp lý chắc chắn khi chưa có LLM/evidence hợp lệ.

## 11. Lưu trữ

### ChromaDB

ChromaDB lưu persistent các collection pháp luật. Docker mount volume để dữ liệu vector không mất khi recreate container.

### Conversation storage

Frontend/backend có API conversation để tạo, đọc và xóa lịch sử. SQLite được dùng cho môi trường hiện tại; có thể thay bằng PostgreSQL khi triển khai production mà không thay đổi retrieval contract.

## 12. Docker và triển khai

Backend chạy trong container:

```text
Docker Compose
  → trust-agent container
  → Uvicorn/FastAPI :8000
  → persistent Chroma volume
```

Frontend deploy trên Vercel. Backend có thể chạy trên máy lab/server và expose qua Cloudflare Tunnel.

```text
Vercel frontend
  → TRUST_AGENT_API_URL
  → Cloudflare Tunnel
  → backend Docker :8000
```

Khi đổi `.env` backend, cần recreate container để Docker nhận cấu hình mới:

```bash
docker compose up -d --force-recreate trust-agent
```

## 13. Điểm cần lưu ý khi phát triển

- Không đổi canonical domain tùy ý.
- Không gọi HTTP tới chính backend từ Router; dùng direct Python dispatch.
- Không bỏ filter domain trong retrieval/document lookup.
- Không để LLM tự tạo citation metadata.
- Không dùng query accent-folded làm query chính cho retrieval.
- Không đưa key vào Git, Docker image, frontend hoặc log.
- Khi thêm domain mới, chỉ thêm domain config, corpus, collection, agent tools và test isolation; không copy toàn bộ business logic.

## 14. Tóm tắt một request hoàn chỉnh

```text
Người dùng hỏi
  → frontend gửi /router/ask
  → clean_query giữ nguyên nội dung pháp lý
  → Router tạo routing_query để phân loại
  → Router tạo sub-query theo domain
  → ReAct Agent gọi search tool domain-locked
  → dense + BM25 + RRF lấy evidence
  → LLM tạo câu trả lời ngắn gọn
  → verifier kiểm tra citation IDs
  → Router tổng hợp các domain verified
  → frontend render answer + citations + status
```
