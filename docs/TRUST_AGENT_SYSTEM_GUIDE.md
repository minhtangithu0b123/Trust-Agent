# Trust Agent — Tài liệu tổng hợp hệ thống và lý thuyết

> Tài liệu này giải thích Trust Agent từ nền tảng lý thuyết đến kiến trúc triển khai thực tế.

## 1. Trust Agent là gì?

Trust Agent là trợ lý tra cứu pháp luật Việt Nam theo mô hình **Retrieval-Augmented Generation (RAG)**. Hệ thống nhận câu hỏi, xác định lĩnh vực, truy xuất evidence, nhờ LLM diễn giải và kiểm tra citation bằng code.

Ba domain hiện tại:

```text
traffic    → pháp luật giao thông
labor      → pháp luật lao động
accounting → kế toán và thuế
```

Mục tiêu là trả lời dựa trên corpus đã ingest và nói rõ khi dữ liệu không đủ; hệ thống không thay thế tư vấn pháp lý chuyên nghiệp.

## 2. Kiến trúc tổng thể

```text
Người dùng
   ↓
Next.js Frontend (web/)
   ↓ /api proxy
FastAPI Backend (crawl/app/main.py)
   ↓
LangGraph Router
   ├── Traffic Agent
   ├── Labor Agent
   └── Accounting Agent
          ↓
  Dense + BM25 + RRF
          ↓
 ChromaDB persistent
          ↓
 LLM + Citation Verifier
          ↓
 answer + citations + status
```

Các lớp chính:

1. **Frontend**: nhập câu hỏi, render answer/citation/history.
2. **API**: validate request, normalize query và dispatch.
3. **Router**: classify, fan-out song song và synthesize.
4. **Domain Agent**: chọn tool và lấy evidence domain-specific.
5. **Retrieval**: dense semantic search, BM25 và RRF.
6. **Generation**: LLM diễn giải context.
7. **Verification**: kiểm tra citation và status.
8. **Storage**: corpus JSON, ChromaDB persistent và conversation database.

## 3. Lý thuyết RAG

### 3.1. Vấn đề của LLM thuần túy

LLM có thể trả lời trôi chảy nhưng không bảo đảm thông tin còn hiệu lực, đúng Điều/Khoản, đúng mức phạt hoặc có citation thật. Hiện tượng tạo thông tin nghe hợp lý nhưng không có nguồn gọi là **hallucination**.

### 3.2. RAG giải quyết thế nào?

RAG tách câu trả lời thành:

```text
Retrieval: tìm dữ liệu liên quan
Generation: diễn giải dữ liệu
```

Luồng:

```text
query → retrieve evidence → build context → LLM → verify → response
```

RAG không tự bảo đảm đúng. Chất lượng còn phụ thuộc corpus, chunking, embedding, retrieval, prompt và verifier.

## 4. Dữ liệu, chunking và metadata

Chunk pháp luật nên giữ cấu trúc:

```text
Văn bản → Chương → Điều → Khoản → nội dung
```

Metadata chuẩn:

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
Metadata dùng để lọc domain, tạo citation và hiển thị nguồn. Không nên chỉ nhét metadata vào text rồi bắt LLM tự trích xuất.

### Chunking tốt

Chunk nên giữ đầy đủ số Điều/Khoản và claim liên quan. Không nên cắt giữa mức tiền, đối tượng áp dụng và hình thức xử phạt. Nếu corpus đã có ranh giới pháp lý, dùng ranh giới đó trước kích thước ký tự.

### Chunking xấu

```text
Chunk 1: phạt tiền từ 6.000.000 đồng đến
Chunk 2: 8.000.000 đồng đối với người điều khiển...
```

Chunk tốt giữ cả câu và metadata Điều/Khoản.

## 5. Query normalization và expansion

### `original_query`

NFC, trim và gộp whitespace nhưng giữ dấu tiếng Việt, số, `/`, `-`, `.`, punctuation và số hiệu. Dùng cho retrieval, LLM, citation và response.

```text
"  Nghị định   168/2024/NĐ-CP  "
→ "Nghị định 168/2024/NĐ-CP"
```

### `routing_query`

Lowercase, bỏ dấu, map `đ` thành `d`, chỉ dùng cho keyword routing.

```text
"Mức phạt nồng độ cồn"
→ "muc phat nong do con"
```

Không dùng query bỏ dấu làm legal context chính.

### Query expansion

Expansion bổ sung thuật ngữ canonical để tăng recall:

```text
muc phat nong do con
→ Mức phạt nồng độ cồn, xử phạt vi phạm nồng độ cồn
```

Expansion không được thêm Điều, Khoản, mức tiền, ngày hiệu lực hoặc citation chưa có trong evidence.

## 6. Dense semantic retrieval

Embedding biến text thành vector nhiều chiều:

```text
"mức phạt nồng độ cồn" → [0.12, -0.04, 0.88, ...]
```

Các text có nghĩa gần nhau thường có vector gần nhau. Một similarity phổ biến là cosine:

```text
cosine(A, B) = (A · B) / (||A|| ||B||)
```

Ưu điểm: hiểu ngữ nghĩa, từ đồng nghĩa và cách diễn đạt khác nhau. Nhược điểm: có thể bỏ qua số hiệu/keyword chính xác và nhầm các Điều gần nghĩa. Vì vậy dense search nên kết hợp BM25.

## 7. BM25 sparse retrieval

BM25 là keyword retrieval, dựa trên tần suất token, độ hiếm của token trong corpus và độ dài document.

Nó mạnh với:

- `Nghị định 168/2024/NĐ-CP`;
- `Điều 8`, `Khoản 9`;
- `nồng độ cồn`;
- mức tiền và loại phương tiện.

BM25 yếu hơn dense khi người dùng dùng từ đồng nghĩa. BM25 index cần được xây theo domain và refresh sau ingest; nếu không, Chroma có dữ liệu mới nhưng nhánh keyword vẫn cũ.

## 8. Hybrid retrieval và RRF

```text
dense semantic search ─┐
                       ├─ RRF → top-k evidence
BM25 keyword search ───┘
```

Hybrid search lấy ứng viên từ cả hai retriever rồi hợp nhất. RRF không cộng trực tiếp score vì dense và BM25 có thang đo khác nhau:

```text
RRF(d) = Σ 1 / (c + rank_i(d))
```

`rank_i(d)` là rank của document trong retriever i; `c` thường dùng giá trị lớn như 60. Document xuất hiện tốt ở cả dense và BM25 được ưu tiên.

RRF chỉ đo độ liên quan, không chứng minh claim pháp lý đúng.

## 9. ChromaDB

ChromaDB lưu embedding, text và metadata trong các collection persistent:

```text
legal_traffic
legal_labor
legal_accounting
```

Ingest pipeline:

```text
JSON corpus → validate/normalize → text + metadata → embedding → Chroma
```

Ingest nên idempotent để chạy lại không tạo document trùng. Mọi retrieval và document lookup phải filter đúng domain.

## 10. Router đa domain

Router dùng LangGraph:

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

Classifier nhận original query có dấu. LLM structured output chỉ được trả `traffic`, `labor`, `accounting`. Khi LLM lỗi, keyword fallback dùng routing query. Khi query mơ hồ, trả `needs_clarification`.

Router state có query, k, classifications, results, final answer, final citations và status. `results` cần reducer cộng danh sách để output parallel không ghi đè nhau.

Router chỉ điều phối. Domain Agent mới gọi tool và xử lý evidence.

## 11. Agent và ReAct

Agent có thể quyết định hành động, gọi tool, quan sát kết quả và tiếp tục hoặc kết thúc.

```text
query → decide → tool → observe → decide → tool/finalize
```

ReAct là Reasoning + Acting. Không đưa chain-of-thought ra API; chỉ log thông tin an toàn như tool name, số bước, số evidence và status.

Mỗi domain có hai tool:

```text
search_<domain>_law(query, k)
get_<domain>_document(document_id)
```

Domain được khóa trong code:

```python
search_traffic_law(query):
    return search(query, domain="traffic")
```

Không dùng tool chung nhận domain từ LLM vì có thể gây cross-domain contamination.

Shared agent base nên chứa loop, max steps, timeout, provider error handling, structured output và citation verification. Domain module chỉ định prompt, collection, tool và query expansion.

## 12. LangGraph theory

- **State**: dữ liệu đi qua graph;
- **Node**: hàm xử lý một bước;
- **Edge**: chuyển tiếp;
- **Conditional edge**: chuyển theo điều kiện;
- **Send**: fan-out;
- **Reducer**: merge output;
- **START/END**: lifecycle graph.

LangGraph phù hợp workflow có nhiều nhánh, agent loop và state rõ ràng. Nó không tự làm retrieval tốt hơn; nó giúp điều phối có cấu trúc và kiểm soát được.

## 13. LLM generation và grounded answer

LLM nhận legal context gồm các evidence đã retrieve. Prompt phải yêu cầu:

- chỉ dùng evidence;
- không dùng kiến thức ngoài;
- không bịa Điều/Khoản/số tiền/ngày hiệu lực;
- trả tiếng Việt ngắn gọn;
- phân biệt `Quy định pháp luật` và `Suy luận theo tình huống`;
- nói rõ khi evidence thiếu;
- không copy nguyên văn cả chunk.

Relevant excerpt giúp giảm context, latency và xu hướng LLM bưng nguyên đoạn luật vào câu trả lời.

## 14. Citation verification

LLM chỉ trả:

```json
{
  "answer": "...",
  "cited_document_ids": ["doc-1"]
}
```

Nếu evidence IDs là `{A, B, C}`, cited IDs hợp lệ phải thỏa:

```text
cited_ids ⊆ retrieved_ids
```

Code lấy metadata thật để dựng citation. Citation hợp lệ gồm document ID, số hiệu, tên văn bản, Chương, Điều, Khoản và source.

Citation có mặt không có nghĩa claim chắc chắn được hỗ trợ hoàn toàn. Để kiểm tra sâu hơn cần claim extraction và semantic claim-support verification.

## 15. Guardrail

Guardrail là lớp kiểm soát độc lập với LLM:

```text
Input
 → normalization
 → routing
 → domain lock
 → tool validation
 → retrieval filter
 → prompt policy
 → structured output
 → citation verification
 → safe status
```

### Input guardrail

Query không rỗng, `k` hợp lệ, độ dài giới hạn, domain canonical và schema request đúng.

### Domain guardrail

Traffic chỉ dùng `legal_traffic`; Labor chỉ dùng `legal_labor`; Accounting chỉ dùng `legal_accounting`.

### Tool guardrail

Tool có schema, timeout, giới hạn input, giới hạn k, không gọi URL tùy ý, không đọc secret và không nhận domain tự do.

### Evidence guardrail

Evidence là dữ liệu, không phải instruction. Nên đặt trong `BEGIN EVIDENCE`/`END EVIDENCE`, giới hạn kích thước và nói rõ với LLM rằng evidence không có quyền thay đổi system policy.

### Execution guardrail

Agent cần giới hạn 4–6 bước, timeout, số lần gọi cùng tool, recursion depth và kích thước state. Không trả tool trace/chain-of-thought cho frontend.

### Output guardrail

Final output phải theo schema; bỏ field lạ; không cho LLM tự tạo citation URL/metadata cuối cùng.

### Status guardrail

`verified` chỉ dùng khi provider thành công, evidence tồn tại, citation hợp lệ và answer không vượt evidence.

`insufficient_evidence` dùng khi không có evidence, evidence yếu, cited ID invalid, agent hết bước hoặc answer chứa:

```text
Chưa đủ căn cứ từ dữ liệu hiện có để kết luận.
```

`provider_error` dùng khi API key/model/quota/timeout/provider lỗi. `needs_clarification` dùng khi query mơ hồ.

### Security guardrail

API key chỉ nằm ở backend environment/secret manager. Không commit `.env`, không dùng `NEXT_PUBLIC_*`, không log key và không expose Chroma/database ra Internet.

## 16. Conversation và memory

Conversation storage lưu câu hỏi, câu trả lời, citation và metadata phiên. History không tự động là evidence.

Follow-up như `còn xe hơi` cần context hoặc memory chính thức. Không nên tự suy đoán domain nếu state chưa được kiểm soát. Citation của request hiện tại phải lấy từ evidence của request hiện tại.

## 17. Status API

```text
verified
insufficient_evidence
provider_error
needs_clarification
```

`verified` nên hiểu là “đã qua kiểm tra hệ thống và có căn cứ trong corpus hiện tại”, không phải chứng nhận tư vấn pháp lý tuyệt đối.

## 18. Đánh giá retrieval

### Recall@k

```text
Recall@k = số query có evidence đúng trong top-k / tổng số query
```

### MRR

```text
RR  = 1 / rank của evidence đúng đầu tiên
MRR = mean(RR)
```

Recall/MRR là metric retrieval trên benchmark, không phải độ chính xác pháp lý tổng quát.

Bộ test nên có query có dấu/không dấu, số hiệu, Điều/Khoản, từ đồng nghĩa, follow-up, query mơ hồ, query ngoài corpus và trường hợp dễ nhầm giữa phương tiện.

Đánh giá riêng:

| Tầng | Câu hỏi |
|---|---|
| Data | Corpus đúng và đủ không? |
| Retrieval | Evidence đúng có trong top-k không? |
| Grounding | Answer có vượt evidence không? |
| Citation | Citation có đúng metadata không? |
| Status | Có reject khi thiếu căn cứ không? |
| Concision | Có trả lời đúng trọng tâm không? |
| Latency | Response có ổn định không? |
| Safety | Prompt injection có bị chặn không? |

## 19. Tối ưu latency

Nguồn latency gồm tải embedding lần đầu, dense search, BM25 refresh, classification, nhiều vòng ReAct, final LLM, network và Cloudflare Tunnel.

Biện pháp:

- preload/cache embedding model;
- cache Chroma client;
- cache BM25 theo domain;
- dùng keyword fallback khi query rõ;
- giới hạn k và agent steps;
- không lookup lại khi evidence đủ;
- giảm context bằng relevant excerpt;
- fan-out Router song song;
- đo riêng retrieval time và LLM time.

Không bỏ domain filter hoặc citation verifier chỉ để nhanh hơn.

## 20. Các lỗi thường gặp

### Provider error

Key expired/revoked, `.env` sai, container chưa recreate, model/provider sai, quota hoặc timeout.

### Retrieval yếu

Query chung, expansion thiếu, chunk sai, embedding không phù hợp, BM25 chưa refresh hoặc thiếu reranker.

### Trộn domain

Quên metadata filter, dùng nhầm collection hoặc cho LLM truyền domain tùy ý.

### LLM copy nguyên văn

Context quá dài hoặc prompt không yêu cầu trả lời ngắn và grounded.

## 21. Triển khai

```text
Frontend → Vercel
Backend  → Docker/server
Public backend → Cloudflare Tunnel
```

Docker Compose chạy Uvicorn ở port 8000 và mount Chroma persistent volume. Khi đổi `.env` cần recreate:

```bash
docker compose up -d --force-recreate trust-agent
```

Frontend chỉ giữ URL backend. OpenAI key chỉ ở backend.

## 22. Hướng phát triển

- cross-encoder reranker;
- effective-date/version filtering;
- văn bản sửa đổi/thay thế;
- claim extraction;
- semantic claim-to-evidence verifier;
- benchmark lớn theo domain;
- tracing/observability;
- PostgreSQL production storage;
- named Cloudflare Tunnel;
- memory/checkpointer;
- HITL cho câu hỏi rủi ro cao;
- streaming response.

Khi thêm domain, thêm domain config, corpus, collection, prompt, tools và tests; không copy toàn bộ business logic.

## 23. Tóm tắt dễ nhớ

```text
RAG tìm căn cứ.
Dense hiểu nghĩa.
BM25 giữ keyword chính xác.
RRF hợp nhất thứ hạng.
Chroma lưu vector và metadata.
Agent quyết định tool.
Router điều phối domain.
Guardrail giới hạn hành vi.
Citation verifier kiểm tra nguồn.
Status nói rõ mức độ căn cứ.
```

Không có một kỹ thuật đơn lẻ nào bảo đảm câu trả lời pháp luật đúng. Độ tin cậy đến từ sự kết hợp giữa dữ liệu tốt, retrieval tốt, agent bị giới hạn, prompt grounded và verification deterministic.
