import json
from pathlib import Path

from app.config import get_settings
from app.retrieval import get_hybrid_retriever


CASES = [
    {"query": "Người lao động có quyền đơn phương chấm dứt hợp đồng khi nào?", "expected": "Điều 35"},
    {"query": "Thời giờ làm việc bình thường tối đa là bao nhiêu?", "expected": "Điều 105"},
    {"query": "Quy định về làm thêm giờ của người lao động", "expected": "Điều 107"},
    {"query": "Hình thức và kỳ hạn trả lương", "expected": "Điều 96"},
    {"query": "Người lao động được nghỉ hằng năm bao nhiêu ngày?", "expected": "Điều 113"},
    {"query": "Thời gian thử việc được quy định thế nào?", "expected": "Điều 25"},
    {"query": "Hợp đồng lao động phải có nội dung chủ yếu gì?", "expected": "Điều 21"},
    {"query": "Quy định về nghỉ thai sản của lao động nữ", "expected": "Điều 139"},
    {"query": "Kỷ luật lao động và các hình thức xử lý", "expected": "Điều 124"},
    {"query": "Tuổi nghỉ hưu của người lao động", "expected": "Điều 169"},
]


def main() -> None:
    retriever = get_hybrid_retriever(get_settings(), domain="labor")
    rows = []
    for case in CASES:
        results = retriever.search(case["query"], k=5)
        returned = [result.document.metadata.get("dieu", "") for result in results]
        haystack = " ".join(returned + [result.document.page_content for result in results])
        passed = case["expected"].casefold() in haystack.casefold()
        rows.append({**case, "top_k_returned": returned, "pass": passed})
        print(f"{'PASS' if passed else 'FAIL'} | {case['expected']} | {case['query']} | {returned}")
    output = Path("reports") / "retrieval_evaluation.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nPASS={sum(row['pass'] for row in rows)}/{len(rows)}")
    print(f"Report: {output}")


if __name__ == "__main__":
    main()
