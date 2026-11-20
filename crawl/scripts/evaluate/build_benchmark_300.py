"""Build a 300-case retrieval benchmark: 100 cases per legal domain."""
from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("benchmark_v3.jsonl")
TEMPLATES = [
    "{topic} được quy định như thế nào?",
    "Cho tôi biết quy định pháp luật về {topic}.",
    "Khi nào áp dụng quy định về {topic}?",
    "{topic} có những điều kiện hoặc mức xử lý nào?",
    "Căn cứ pháp lý nào nói về {topic}?",
]

DOMAINS = {
    "traffic": [
        ("nồng độ cồn khi lái xe máy", ["nồng độ cồn", "xe mô tô"]),
        ("nồng độ cồn khi lái xe ô tô", ["nồng độ cồn", "ô tô"]),
        ("không đội mũ bảo hiểm", ["mũ bảo hiểm"]),
        ("vượt đèn đỏ", ["đèn đỏ"]),
        ("đi ngược chiều", ["đi ngược chiều"]),
        ("chạy quá tốc độ", ["tốc độ"]),
        ("không có giấy phép lái xe", ["giấy phép lái xe"]),
        ("sử dụng điện thoại khi lái xe", ["điện thoại"]),
        ("không chấp hành kiểm tra nồng độ cồn", ["nồng độ cồn"]),
        ("dừng đỗ xe không đúng quy định", ["dừng", "đỗ"]),
        ("chuyển làn đường", ["chuyển làn"]),
        ("chuyển hướng không báo hiệu", ["chuyển hướng"]),
        ("nhường đường cho xe ưu tiên", ["xe ưu tiên"]),
        ("gây tai nạn giao thông", ["tai nạn giao thông"]),
        ("chở quá số người quy định", ["chở người"]),
        ("chở hàng cồng kềnh bằng xe máy", ["chở hàng"]),
        ("xe máy đi vào đường cao tốc", ["đường cao tốc"]),
        ("xe không có gương chiếu hậu", ["gương chiếu hậu"]),
        ("không bật đèn chiếu sáng", ["đèn chiếu sáng"]),
        ("không chấp hành hiệu lệnh của cảnh sát giao thông", ["hiệu lệnh"]),
    ],
    "labor": [
        ("nghỉ hằng năm", ["nghỉ hằng năm"]),
        ("hợp đồng lao động", ["hợp đồng lao động"]),
        ("thời giờ làm việc bình thường", ["thời giờ làm việc"]),
        ("ngày nghỉ lễ tết", ["nghỉ lễ", "tết"]),
        ("mức lương tối thiểu", ["mức lương tối thiểu"]),
        ("tiền lương làm thêm giờ", ["làm thêm giờ", "tiền lương"]),
        ("kỷ luật lao động", ["kỷ luật lao động"]),
        ("đơn phương chấm dứt hợp đồng", ["đơn phương chấm dứt"]),
        ("thời gian thử việc", ["thử việc"]),
        ("nghỉ thai sản", ["thai sản"]),
        ("bảo hiểm xã hội của người lao động", ["bảo hiểm xã hội"]),
        ("tai nạn lao động", ["tai nạn lao động"]),
        ("an toàn vệ sinh lao động", ["an toàn lao động"]),
        ("nghỉ việc riêng", ["nghỉ việc riêng"]),
        ("kỳ hạn trả lương", ["trả lương"]),
        ("thời giờ nghỉ ngơi", ["thời giờ nghỉ ngơi"]),
        ("người lao động cao tuổi", ["lao động cao tuổi"]),
        ("lao động chưa thành niên", ["lao động chưa thành niên"]),
        ("sa thải người lao động", ["sa thải"]),
        ("tranh chấp lao động", ["tranh chấp lao động"]),
    ],
    "accounting": [
        ("nguyên tắc kế toán", ["nguyên tắc kế toán"]),
        ("chứng từ kế toán", ["chứng từ kế toán"]),
        ("hóa đơn điện tử", ["hóa đơn điện tử"]),
        ("thuế giá trị gia tăng", ["thuế giá trị gia tăng"]),
        ("kê khai thuế", ["kê khai", "thuế"]),
        ("quyết toán thuế", ["quyết toán thuế"]),
        ("lưu trữ tài liệu kế toán", ["lưu trữ", "kế toán"]),
        ("báo cáo tài chính", ["báo cáo tài chính"]),
        ("tổ chức công tác kế toán", ["công tác kế toán"]),
        ("kế toán trưởng", ["kế toán trưởng"]),
        ("ghi nhận tài sản kế toán", ["tài sản", "ghi nhận"]),
        ("hủy chứng từ kế toán", ["chứng từ kế toán"]),
        ("kiểm kê tài sản", ["kiểm kê tài sản"]),
        ("ký báo cáo tài chính", ["báo cáo tài chính"]),
        ("vi phạm pháp luật về kế toán", ["vi phạm", "kế toán"]),
        ("sổ kế toán và khóa sổ", ["sổ kế toán"]),
        ("thời hạn nộp báo cáo tài chính", ["báo cáo tài chính", "thời hạn"]),
        ("thuế thu nhập doanh nghiệp", ["thuế thu nhập doanh nghiệp"]),
        ("hóa đơn sai thông tin", ["hóa đơn"]),
        ("quyền và nghĩa vụ của đơn vị kế toán", ["đơn vị kế toán"]),
    ],
}


def main() -> None:
    rows: list[dict] = []
    for domain, topics in DOMAINS.items():
        for topic_index, (topic, keywords) in enumerate(topics):
            for template_index, template in enumerate(TEMPLATES):
                rows.append({
                    "id": f"{domain}-{topic_index + 1:02d}-{template_index + 1:02d}",
                    "domain": domain,
                    "query": template.format(topic=topic),
                    "expected_keywords": keywords,
                })
    OUT.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
    print(f"wrote {len(rows)} cases to {OUT}")


if __name__ == "__main__":
    main()
