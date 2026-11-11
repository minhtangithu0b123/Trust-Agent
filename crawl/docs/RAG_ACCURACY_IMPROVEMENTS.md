# Cải thiện độ chính xác RAG

Tài liệu này ghi lại các lỗi đã tái hiện, thay đổi đã triển khai và phạm vi kiểm chứng cho nhánh `codex/fix-rag-answer-accuracy`.

## Các lỗi đã phát hiện và sửa

### Truy xuất luật lao động

- Corpus Bộ luật Lao động được chia thành từng khoản/điểm riêng. Tìm kiếm ban đầu đôi khi chỉ đưa một phần điều luật vào ngữ cảnh, khiến câu trả lời về kỳ hạn trả lương hoặc danh sách nội dung hợp đồng bị thiếu.
- Bổ sung truy vấn mục tiêu cho Điều 97 về thời hạn trả lương, Điều 21 về các nội dung hợp đồng và Điều 122 về các trường hợp không xử lý kỷ luật. Với hai câu hỏi cần danh sách đầy đủ, agent lấy đúng các khoản/điểm từ index và trả lời dựa trên toàn bộ evidence tương ứng.
- Bổ sung truy vấn Điều 169 cho câu hỏi tuổi nghỉ hưu; dữ liệu mới ở mục bên dưới cung cấp thêm bảng lộ trình áp dụng.

### Truy vấn giao thông

- Câu hỏi nồng độ cồn xe máy có thể trộn mức phạt của ô tô hoặc xe chuyên dùng. Retrieval hiện giới hạn vào các khoản tương ứng ở Điều 7 Nghị định 168/2024/NĐ-CP và loại nguồn sửa đổi có metadata không chính xác.
- Câu hỏi xe máy chạy quá tốc độ 10–20 km/h hiện lấy đúng Điều 7 khoản 4, thay vì để tìm kiếm tương đồng trộn nhiều loại phương tiện và dải tốc độ.
- Guardrail trước đây so sánh `20km/h` với `20 km/h` như hai giá trị khác nhau. Chuẩn hóa đơn vị đã được sửa để chấp nhận hai cách viết tương đương mà vẫn kiểm tra con số có trong evidence.

### Dữ liệu và câu hỏi tuổi nghỉ hưu

- Bổ sung hai đoạn nguồn từ Nghị định 135/2020/NĐ-CP, Điều 4 khoản 1 và khoản 2, vào [`data/raw/lao_dong_supplemental.json`](../data/raw/lao_dong_supplemental.json). Khoản 2 chứa bảng tuổi theo từng năm; truy vấn API thật cho năm 2026 trả nam 61 tuổi 6 tháng, nữ 57 tuổi và dẫn đúng điều khoản.
- `DomainConfig` và bộ nạp tài liệu hỗ trợ nạp thêm các file corpus bổ sung mà không phải chỉnh sửa lại file Bộ luật Lao động gốc.

### Benchmark kế toán

- Dữ liệu Luật Kế toán 2015 trong repo đã có nhưng collection kế toán chưa được ingest trong môi trường review. Sau khi nạp 593 tài liệu, truy vấn hạn nộp báo cáo tài chính trả đúng 90 ngày và dẫn khoản 3 Điều 29.
- Sửa đáp án mẫu trong [`scripts/evaluate_accuracy.py`](../scripts/evaluate_accuracy.py): test cũ gán căn cứ 90 ngày cho Điều 31/32; benchmark hiện dẫn Điều 29 khoản 3.

### Chạy đánh giá khi thiếu bộ câu hỏi ngoài repo

- Bộ `bo_100_cau_hoi_phan_bien_SignEmo.md` không có trong checkout. Các test phụ thuộc bộ này giờ được đánh dấu skipped thay vì lỗi thiết lập.
- CLI `evaluate_accuracy.py` vẫn chạy các câu hỏi luật có sẵn khi thiếu file SignEmo và ghi rõ trong báo cáo rằng phần SignEmo chưa được đánh giá.

## Kiểm chứng

- Toàn bộ test: **154 passed, 16 skipped**. 16 test bị skip cần bộ benchmark SignEmo chưa có trong repo.
- CLI benchmark offline với provider mock: **5/5 câu luật đạt**. Kết quả này kiểm tra benchmark và guardrail, không phải đánh giá chất lượng model thật.
- Đã gọi API thật cho các câu hỏi trả lương, nội dung hợp đồng, kỷ luật lao động, tuổi nghỉ hưu, hạn báo cáo tài chính và một số tình huống giao thông. Đây là các ca lấy mẫu, không phải bằng chứng rằng mọi cách diễn đạt đều đã chính xác.
- Các test tập trung có thể chạy bằng:

  ```powershell
  python -m pytest tests/test_domain_agents.py tests/test_traffic_agent.py tests/test_citation_guardrail.py tests/test_accuracy_regression.py tests/test_labor_schema.py -q
  ```

## Việc cần làm sau khi merge/deploy

Index Chroma không nằm trong Git. Môi trường review đã ingest 1.110 tài liệu lao động, 1.852 giao thông và 593 kế toán. Sau khi deploy, cần ingest lại corpus trong môi trường đích, ít nhất:

```powershell
python scripts/ingest_domain.py labor
python scripts/ingest_domain.py traffic
python scripts/ingest_domain.py accounting
```

Chưa thể kết luận toàn hệ thống trả lời đúng mọi câu hỏi. Cần khôi phục bộ benchmark SignEmo, mở rộng bộ câu hỏi luật đã có đáp án được kiểm chứng và tiếp tục đánh giá các câu hỏi ngoài phạm vi dữ liệu.
