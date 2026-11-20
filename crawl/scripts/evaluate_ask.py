"""Offline end-to-end smoke evaluation for grounded /ask using a mock provider."""
import json
from pathlib import Path

from app.answering import GenerationResult, answer_question
from app.config import get_settings


class MockProvider:
    def generate(self, query: str, context: str) -> GenerationResult:
        first = next((line for line in context.splitlines() if line.startswith("[DOCUMENT_ID:")), "")
        document_id = first.removeprefix("[DOCUMENT_ID:").removesuffix("]").strip()
        return GenerationResult(
            answer="Mock: câu trả lời chỉ dựa trên evidence đã truy xuất.",
            cited_document_ids=[document_id] if document_id else [],
        )


CASES = [
    "Thời giờ làm việc bình thường của người lao động là bao nhiêu?",
    "Người lao động được nghỉ hằng năm bao nhiêu ngày?",
    "Khi nào người lao động được đơn phương chấm dứt hợp đồng lao động?",
    "Thời gian thử việc tối đa là bao lâu?",
    "Tiền lương làm thêm giờ được tính như thế nào?",
]


def main() -> None:
    settings = get_settings()
    rows = []
    for query in CASES:
        result = answer_question(query, 5, settings, provider=MockProvider())
        passed = result["status"] == "verified" and bool(result["citations"])
        rows.append({
            "query": query,
            "status": result["status"],
            "top_k_returned": len(result["evidence"]),
            "citations": result["citations"],
            "pass": passed,
        })
        print(f"{'PASS' if passed else 'FAIL'} | {query} | status={result['status']} | evidence={len(result['evidence'])}")
    print(json.dumps({"total": len(rows), "passed": sum(row["pass"] for row in rows), "cases": rows}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()