import logging
import math
import re
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

IntentType = Literal["greeting", "out_of_scope", "in_scope"]

GREETING_MESSAGE = (
    "Xin chào bạn! Tôi là Trợ lý Pháp lý Trust-AGENT. Tôi có thể hỗ trợ bạn tra cứu "
    "và giải đáp các quy định pháp luật Việt Nam về: Giao thông đường bộ, Lao động và "
    "Thuế / Kế toán. Bạn đang cần tìm hiểu vấn đề gì ạ?"
)

OUT_OF_SCOPE_MESSAGE = (
    "Xin lỗi bạn, câu hỏi của bạn nằm ngoài phạm vi tư vấn pháp lý của tôi. "
    "Hệ thống hiện chuyên sâu về 3 lĩnh vực pháp luật Việt Nam: Giao thông, Lao động "
    "và Thuế / Kế toán. Bạn vui lòng đặt câu hỏi liên quan đến các lĩnh vực này để được hỗ trợ nhé!"
)

# Regex fast-paths cho câu chào hỏi, cảm ơn, tạm biệt phổ biến
GREETING_REGEXES = [
    re.compile(r"^(xin\s+)?chào(\s+bạn|\s+ad|\s+bot|\s+anh|\s+chị|\s+em)?(\s+nhe|\s+nhé|\s+ạ)?$", re.IGNORECASE),
    re.compile(r"^(hi|hello|hey)(\s+bot|\s+there|\s+bạn)?(\s+ạ)?$", re.IGNORECASE),
    re.compile(r"^(cảm\s+ơn|thanks|thank\s+you)(\s+bạn|\s+bot|\s+nhiều)?(\s+nhiều)?(\s+nhé|\s+ạ)?$", re.IGNORECASE),
    re.compile(r"^(tạm\s+biệt|bye|goodbye)(\s+bạn|\s+bot)?(\s+nhé|\s+ạ)?$", re.IGNORECASE),
    re.compile(r"^(bạn\s+là\s+ai|bạn\s+làm\s+được\s+gì|giới\s+thiệu\s+bản\s+thân)(\s+đi|\s+ạ)?$", re.IGNORECASE),
]

# Từ khóa đặc trưng của các chủ đề ngoài lề (chitchat, thể thao, văn học, đời sống, thời tiết...)
OUT_OF_SCOPE_KEYWORDS = [
    "thời tiết", "mưa", "nắng", "nhiệt độ", "dự báo",
    "nấu ăn", "món ăn", "ăn gì", "công thức nấu",
    "bài thơ", "làm thơ", "thơ tình", "sáng tác", "viết truyện",
    "bóng đá", "thể thao", "ngoại hạng anh", "world cup",
    "chuyện cười", "kể chuyện cười", "đố vui",
    "uống thuốc gì", "triệu chứng bệnh", "bác sĩ",
    "viết code", "lập trình python", "fix bug",
]

# Từ khóa đặc trưng pháp lý (đảm bảo không chặn nhầm câu hỏi luật)
LEGAL_KEYWORDS = [
    "luật", "nghị định", "thông tư", "điều", "khoản", "điểm", "văn bản",
    "phạt", "giao thông", "đường bộ", "xe máy", "ô tô", "nồng độ cồn", "bằng lái", "tốc độ", "đèn đỏ",
    "lao động", "lương", "nghỉ phép", "sa thải", "hợp đồng", "thử việc", "bảo hiểm", "trợ cấp",
    "thuế", "kế toán", "hóa đơn", "vat", "gtgt", "tncn", "tndn", "khấu trừ", "quyết toán",
]

OUT_OF_SCOPE_PHRASES = [
    "hôm nay ăn gì", "công thức nấu ăn", "dự báo thời tiết", "thời tiết hôm nay",
    "bài thơ tình", "viết bài thơ", "kể chuyện cười", "bóng đá ngoại hạng anh",
    "lập trình code", "triệu chứng bệnh", "hướng dẫn cài win",
]


@dataclass
class IntentCheckResult:
    intent: IntentType
    response: str | None = None
    confidence: float = 1.0


class SemanticIntentGuardrail:
    def __init__(self, settings=None):
        self.settings = settings

    def check_intent(self, query: str) -> IntentCheckResult:
        normalized = query.strip()
        if not normalized:
            return IntentCheckResult(
                intent="greeting",
                response=GREETING_MESSAGE,
                confidence=1.0,
            )

        # 1. Fast-Path: Kiểm tra Regex cho câu chào hỏi, cảm ơn, giới thiệu
        for pattern in GREETING_REGEXES:
            if pattern.search(normalized):
                return IntentCheckResult(
                    intent="greeting",
                    response=GREETING_MESSAGE,
                    confidence=1.0,
                )

        # 2. Fast Keyword Out-of-Scope check
        lower_q = normalized.lower()
        has_out_keyword = any(kw in lower_q for kw in OUT_OF_SCOPE_KEYWORDS) or any(p in lower_q for p in OUT_OF_SCOPE_PHRASES)
        has_legal_keyword = any(kw in lower_q for kw in LEGAL_KEYWORDS)

        # Nếu có từ khóa ngoài lề và không có từ khóa pháp lý
        if has_out_keyword and not has_legal_keyword:
            return IntentCheckResult(
                intent="out_of_scope",
                response=OUT_OF_SCOPE_MESSAGE,
                confidence=1.0,
            )

        # Mặc định cho phép đi tiếp vào luồng Router
        return IntentCheckResult(intent="in_scope", response=None, confidence=1.0)


_guardrail_instance: SemanticIntentGuardrail | None = None


def get_intent_guardrail(settings=None) -> SemanticIntentGuardrail:
    global _guardrail_instance
    if _guardrail_instance is None:
        _guardrail_instance = SemanticIntentGuardrail(settings)
    return _guardrail_instance
