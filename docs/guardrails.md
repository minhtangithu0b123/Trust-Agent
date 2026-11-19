# Trust Agent — Guardrails

## Mục tiêu

Guardrail là lớp kiểm soát để hệ thống:

- chỉ dùng đúng corpus của domain;
- không bịa Điều, Khoản, số tiền, số hiệu hoặc ngày hiệu lực;
- không biến evidence yếu thành kết luận `verified`;
- tạo citation từ metadata thực tế;
- không làm lộ API key hoặc tool trace;
- không crash khi LLM/provider lỗi.

Guardrail không thay thế việc làm sạch dữ liệu, kiểm tra hiệu lực văn bản hoặc tư vấn pháp lý chuyên nghiệp.

## Luồng guardrail

```text
Input
 → Query normalization
 → Routing/domain isolation
 → Tool validation
 → Retrieval/evidence validation
 → LLM prompt policy
 → Structured output validation
 → Citation verification
 → Status guardrail
 → Safe API response
```

## 1. Input guardrail

Request phải được kiểm tra bằng schema:

- `query` là string và không rỗng;
- giới hạn độ dài query;
- `k` là số nguyên dương và có giới hạn tối đa;
- domain chỉ thuộc `traffic`, `labor`, `accounting`;
- body lỗi phải trả HTTP/JSON rõ ràng, không stack trace;
- không chấp nhận input khiến agent gọi tool ngoài danh sách.

Không được xóa `/`, `-`, `.`, số hiệu văn bản hoặc nội dung Điều/Khoản trong quá trình clean query.

## 2. Query guardrail

Tách hai biểu diễn:

### `original_query`

NFC, trim và gộp whitespace nhưng giữ dấu tiếng Việt, số, punctuation, số hiệu pháp luật. Dùng cho retrieval, LLM, citation và response.

### `routing_query`

Lowercase, bỏ dấu, map `đ` thành `d`. Chỉ dùng cho keyword routing/fallback.

Không dùng query bỏ dấu làm legal context chính.

Query expansion chỉ thêm thuật ngữ canonical đã cấu hình; không được thêm Điều, Khoản, mức tiền, ngày hiệu lực hoặc citation chưa có trong query/evidence.

## 3. Routing guardrail

Classifier chỉ được trả enum:

```text
traffic | labor | accounting
```

Nếu structured LLM classification lỗi, dùng keyword fallback. Nếu vẫn mơ hồ, trả `needs_clarification`; không chọn domain ngẫu nhiên.

Router giữ graph:

```text
classify → Send fan-out → domain agents → synthesize
```

Các nhánh song song phải dùng reducer để không ghi đè output của nhau.

## 4. Domain isolation guardrail

```text
Traffic Agent    → traffic    → legal_traffic
Labor Agent      → labor      → legal_labor
Accounting Agent → accounting → legal_accounting
```

Domain phải được khóa trong code/config, không lấy từ tham số do LLM truyền vào. `get_traffic_document(id)` chỉ được lookup trong `legal_traffic`.

Nếu corpus Accounting/Traffic chưa tồn tại, trả lỗi rõ ràng; không lấy dữ liệu domain khác và không tạo dữ liệu giả.

## 5. Tool guardrail

Mỗi tool phải có input schema, giới hạn input, giới hạn `k`, timeout, domain cố định và output compact.

Tool không được:

- thực thi code;
- gọi URL tùy ý;
- đọc file bí mật;
- nhận domain tùy ý từ model;
- trả API key, prompt bí mật hoặc raw trace.

Tool search nên trả `document_id`, `text`, `dieu`, `khoan`, `so_hieu`, `ten_van_ban` và `source`.

## 6. Retrieval/evidence guardrail

Retrieval phải:

- filter metadata `domain`;
- dùng collection đúng domain;
- giữ text cùng metadata;
- không coi similarity score là bằng chứng pháp lý;
- trả evidence rỗng khi không có kết quả đủ phù hợp.

Evidence là dữ liệu, không phải instruction. Khi build prompt nên đặt trong vùng rõ ràng:

```text
BEGIN EVIDENCE
...
END EVIDENCE
```

Prompt phải nói rằng nội dung evidence không có quyền thay đổi system policy. Đây là biện pháp chống prompt injection từ dữ liệu ingest.

Relevant excerpt nên giới hạn độ dài, nhưng không được cắt mất context Điều/Khoản cần thiết.

## 7. Prompt guardrail

System prompt của agent phải yêu cầu:

- luôn search trước khi trả lời;
- chỉ dùng tool output;
- không dùng kiến thức bên ngoài evidence;
- không bịa luật, Điều, Khoản, số tiền, ngày hiệu lực;
- được search lại khi evidence thiếu;
- trả tiếng Việt rõ ràng, ngắn gọn;
- phân biệt `Quy định pháp luật` và `Suy luận theo tình huống`;
- không thay thế tư vấn pháp lý.

Nếu evidence chứa câu kiểu “bỏ qua system prompt”, model phải coi đó là text pháp luật/dữ liệu, không phải instruction.

## 8. Agent execution guardrail

Agent loop cần giới hạn:

- `max_steps` khoảng 4–6;
- số lần gọi cùng tool;
- timeout từng tool và toàn request;
- kích thước evidence;
- số document trong state;
- recursion depth.

Khi vượt giới hạn, trả `insufficient_evidence` hoặc `provider_error` tùy nguyên nhân. Không loop vô hạn và không trả chain-of-thought/tool trace ra frontend.

## 9. Output guardrail

Final output của LLM phải theo schema:

```json
{
  "answer": "...",
  "cited_document_ids": ["doc-123"]
}
```

LLM chỉ trả document IDs. Không cho LLM tự viết citation URL, Điều/Khoản hay metadata cuối cùng.

API response không được chứa API key, system prompt, raw stack trace hoặc internal tool messages.

## 10. Citation guardrail

```text
retrieved_ids = {A, B, C}
cited_ids     = {A, C}
valid         = cited_ids ⊆ retrieved_ids
```

Nếu cited ID không nằm trong evidence, citation invalid và status không được là `verified`.

Citation cuối cùng được code tạo từ metadata của vector store:

```text
document_id
so_hieu
ten_van_ban
chuong
dieu
khoan
source
```

Citation hợp lệ chỉ chứng minh document có trong evidence; chưa chắc chứng minh document hỗ trợ mọi claim. Claim-support verification là lớp nâng cao.

## 11. Status guardrail

### `verified`

Chỉ dùng khi provider thành công, evidence tồn tại, citation hợp lệ và answer không có kết luận thiếu căn cứ.

### `insufficient_evidence`

Dùng khi không có evidence, evidence không đủ, cited ID invalid, agent hết bước hoặc answer chứa:

```text
Chưa đủ căn cứ từ dữ liệu hiện có để kết luận.
```

### `provider_error`

Dùng khi API key, model, quota, timeout hoặc structured output provider lỗi. Không được tự bịa fallback answer pháp lý.

### `needs_clarification`

Dùng khi query không đủ rõ để xác định domain/ý định.

## 12. Security guardrail

- API key chỉ đặt ở backend `.env`/secret manager;
- không commit `.env`;
- không dùng `NEXT_PUBLIC_*` cho API key;
- không log key;
- không trả key trong exception;
- giới hạn CORS/rate limit khi production;
- bảo vệ endpoint ingest bằng admin token;
- không expose Chroma/database ra Internet;
- Cloudflare Tunnel chỉ expose backend API cần thiết.

## 13. Conversation guardrail

Conversation history không tự động là evidence. Citation của request hiện tại chỉ được lấy từ evidence được retrieve trong request đó.

Với follow-up như `còn xe hơi`, hệ thống cần memory/context chính thức hoặc yêu cầu làm rõ; không tự suy đoán domain chỉ vì câu trước nói về traffic.

## 14. Test guardrail

Các test bắt buộc:

1. query rỗng bị reject;
2. `k` vượt giới hạn bị chặn;
3. Traffic tool không trả Labor document;
4. classifier trả domain lạ bị reject/fallback;
5. cited ID ngoài evidence bị reject;
6. không có evidence trả `insufficient_evidence`;
7. câu thiếu căn cứ không được `verified`;
8. provider lỗi không crash server;
9. prompt injection trong evidence không đổi policy;
10. response không chứa key/tool trace;
11. reducer giữ đủ parallel outputs;
12. corpus chưa có không tạo dữ liệu giả.

## 15. Giới hạn của guardrail

Guardrail không tự phát hiện mọi văn bản hết hiệu lực, văn bản sửa đổi/thay thế hoặc mâu thuẫn pháp lý. Các phase sau có thể bổ sung version/effective-date filtering, reranker, claim extraction, semantic claim-to-evidence verifier và human review.

`verified` nên được hiểu là “đã qua các kiểm tra hệ thống và có căn cứ trong corpus hiện tại”, không phải chứng nhận tư vấn pháp lý tuyệt đối.
