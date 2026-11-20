# Trust Agent: Agent và Retrieval

Tài liệu này mô tả RAG, ReAct Agent, LangGraph, dense retrieval, BM25, hybrid search, RRF, chunking, metadata filtering, citation verification và đánh giá hệ thống.

## Luồng tổng quát

```text
query → normalize → route → retrieve → context → LLM → verify citation → response
```

## ReAct Agent

Agent quyết định tool, quan sát evidence và có thể search lại trước khi trả lời. Mỗi domain dùng tool khóa cứng domain, giới hạn 4–6 bước và không trả chain-of-thought.

```text
query → decide → search tool → observe evidence → lookup/search again → final answer → verifier
```

Traffic, Labor và Accounting dùng shared loop; chỉ khác domain, prompt, collection và tool.

## Retrieval

Dense retrieval dùng embedding để tìm tài liệu tương đồng ngữ nghĩa. BM25 tìm keyword chính xác như số hiệu, Điều, Khoản và mức phạt. Hybrid retrieval chạy cả hai rồi hợp nhất.

```text
dense semantic search ─┐
                       ├─ RRF → top-k evidence
BM25 keyword search ───┘
```

RRF tính theo rank:

```text
RRF(d) = Σ 1 / (c + rank_i(d))
```

Document xuất hiện tốt ở cả hai retriever được ưu tiên. RRF chỉ đo độ liên quan, không chứng minh claim pháp lý.

## Chunk và metadata

Chunk pháp luật nên giữ `Văn bản → Chương → Điều → Khoản`. Metadata gồm `id`, `domain`, `so_hieu`, `ten_van_ban`, `chuong`, `dieu`, `khoan`, `source`, `effective_from`, `status`.

Retrieval bắt buộc filter đúng domain. Traffic không được lấy labor/accounting dù keyword giống nhau.

## Query

`original_query` giữ dấu, số, `/`, `-`, `.`, số hiệu và dùng cho retrieval/LLM/response. `routing_query` lowercase, bỏ dấu và chỉ dùng cho routing fallback. Query expansion chỉ thêm thuật ngữ canonical, không bịa Điều/Khoản hay mức tiền.

## Citation

LLM chỉ trả `cited_document_ids`. Code đối chiếu các ID này với evidence đã retrieve, sau đó tạo citation từ metadata thực tế. ID ngoài evidence là invalid. Answer thiếu evidence phải là `insufficient_evidence`, không phải `verified`.

## Đánh giá

`Recall@k` đo evidence đúng có trong top-k. `MRR` đo vị trí evidence đúng đầu tiên:

```text
RR = 1 / rank
MRR = mean(RR)
```

Đánh giá riêng retrieval, grounding, citation, status, độ ngắn gọn và safety. Metric trên benchmark không phải độ chính xác pháp lý tổng quát.

## Tối ưu

Preload embedding model, cache Chroma/BM25, refresh BM25 sau ingest, giới hạn k/tool steps, giảm context bằng relevant excerpt và chạy các nhánh Router song song. Không bỏ citation verifier để giảm latency.
