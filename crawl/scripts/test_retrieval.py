from app.config import get_settings
from app.vectorstore import search_labor


QUESTIONS = [
    "Người lao động có quyền đơn phương chấm dứt hợp đồng lao động khi nào?",
    "Thời giờ làm việc bình thường của người lao động được quy định ra sao?",
    "Người sử dụng lao động phải trả lương như thế nào và vào thời điểm nào?",
]


if __name__ == "__main__":
    for question in QUESTIONS:
        print(f"\nQUESTION: {question}")
        for rank, document in enumerate(search_labor(get_settings(), question, k=3), start=1):
            meta = document.metadata
            preview = document.page_content[:300].replace("\n", " ")
            print(f"{rank}. {meta.get('dieu')} / {meta.get('khoan')} - {meta.get('ten_van_ban')}")
            print(f"   source={meta.get('source')}\n   {preview}...")
