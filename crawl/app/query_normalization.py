import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")


def clean_query(text: str) -> str:
    """Apply safe cleanup while preserving legal text and punctuation."""
    normalized = unicodedata.normalize("NFC", text)
    return _WHITESPACE.sub(" ", normalized).strip()


def normalize_for_routing(text: str) -> str:
    """Return an accent-folded representation used only by routing rules."""
    cleaned = clean_query(text).casefold()
    decomposed = unicodedata.normalize("NFD", cleaned)
    without_marks = "".join(
        character for character in decomposed
        if unicodedata.category(character) != "Mn"
    )
    folded = without_marks.replace("đ", "d")
    return _WHITESPACE.sub(" ", folded).strip()


_RETRIEVAL_EXPANSIONS = {
    "traffic": (
        ("nong do con", "nồng độ cồn", "xử phạt vi phạm nồng độ cồn"),
        ("muc phat", "mức phạt vi phạm hành chính"),
        ("xe may", "xe mô tô, xe gắn máy"),
        (
            "vuot den do",
            "không chấp hành hiệu lệnh của đèn tín hiệu giao thông",
        ),
        ("o to", "ô tô"),
        ("tai nan", "tai nạn giao thông"),
    ),
    "labor": (
        ("quyen loi", "quy\u1ec1n l\u1ee3i ng\u01b0\u1eddi lao \u0111\u1ed9ng", "quy\u1ec1n v\u00e0 ngh\u0129a v\u1ee5 c\u1ee7a ng\u01b0\u1eddi lao \u0111\u1ed9ng"),
        ("quyen cua nguoi lao dong", "quy\u1ec1n v\u00e0 ngh\u0129a v\u1ee5 c\u1ee7a ng\u01b0\u1eddi lao \u0111\u1ed9ng"),
        ("hop dong lao dong", "hợp đồng lao động"),
        ("hop dong thu viec", "hợp đồng thử việc", "thời gian thử việc"),
        ("thu viec", "thời gian thử việc", "hợp đồng thử việc", "không quá"),
        ("nghi phep", "nghỉ hằng năm, nghỉ phép"),
        ("luong", "tiền lương"),
        ("bao hiem xa hoi", "bảo hiểm xã hội"),
        ("tai nan lao dong", "tai nạn lao động"),
    ),
    "accounting": (
        ("ca nhan kinh doanh", "cá nhân kinh doanh", "hộ kinh doanh", "nghĩa vụ thuế"),
        ("loai thue", "các loại thuế phải nộp", "nghĩa vụ thuế"),
        ("nhung loai thue", "các loại thuế phải nộp", "nghĩa vụ thuế"),
        ("nguyen tac ke toan", "nguyên tắc kế toán", "Luật Kế toán 2015 Điều 6"),
        ("chung tu ke toan", "chứng từ kế toán"),
        ("so ke toan", "sổ kế toán"),
        ("bao cao tai chinh", "báo cáo tài chính"),
        ("ke toan truong", "kế toán trưởng"),
        ("luu tru tai lieu ke toan", "lưu trữ tài liệu kế toán"),
        ("hoa don dien tu", "hóa đơn điện tử"),
        ("thue gia tri gia tang", "thuế giá trị gia tăng"),
        ("ke toan", "kế toán"),
        ("quyet toan thue", "quyết toán thuế"),
    ),
}

_RETRIEVAL_EXPANSIONS["traffic"] = _RETRIEVAL_EXPANSIONS["traffic"] + (
    ("mu bao hiem", "không đội mũ bảo hiểm", "Điều khiển xe mô tô, xe gắn máy"),
    ("toc do", "vượt quá tốc độ", "giới hạn tốc độ"),
    ("10 20 km h", "vượt quá tốc độ từ 10 km/h đến 20 km/h"),
    ("025 04 mg l", "nồng độ cồn từ 0,25 đến 0,4 mg/l khí thở"),
)

_RETRIEVAL_EXPANSIONS["accounting"] = _RETRIEVAL_EXPANSIONS["accounting"] + (
    ("kiem tra thue", "ki\u1ec3m tra thu\u1ebf", "tr\u01b0\u1eddng h\u1ee3p ki\u1ec3m tra thu\u1ebf", "quy\u1ebft \u0111\u1ecbnh ki\u1ec3m tra thu\u1ebf"),
    ("cuong che", "c\u01b0\u1ee1ng ch\u1ebf thi h\u00e0nh quy\u1ebft \u0111\u1ecbnh h\u00e0nh ch\u00ednh v\u1ec1 thu\u1ebf"),
    ("hoan thue", "ho\u00e0n thu\u1ebf gi\u00e1 tr\u1ecb gia t\u0103ng"),
    ("mien thue", "mi\u1ec5n thu\u1ebf, gi\u1ea3m thu\u1ebf"),
)

_SCENARIO_MARKERS = (
    "truong hop", "ngoai le", "dieu kien", "co phai", "khi nao",
    "day du", "quy dinh", "ap dung", "hien nay", "truoc", "sau",
)


def build_scenario_queries(query: str, domain: str) -> list[str]:
    """Create deterministic coverage queries for condition-heavy questions.

    This is deliberately rule-based: it broadens evidence coverage without
    asking the LLM to invent legal exceptions. Ordinary single-fact queries
    keep their original low-latency retrieval path.
    """
    cleaned = clean_query(query)
    routing = normalize_for_routing(cleaned)
    if not cleaned or not any(marker in routing for marker in _SCENARIO_MARKERS):
        return []

    templates = {
        "traffic": (
            "{q} mức phạt điều khoản áp dụng",
            "{q} hình thức xử phạt bổ sung trừ điểm tước giấy phép",
            "{q} điều kiện ngoại lệ đối tượng áp dụng",
        ),
        "labor": (
            "{q} điều kiện đối tượng áp dụng",
            "{q} trường hợp ngoại lệ và giới hạn",
            "{q} căn cứ điều khoản thời điểm áp dụng",
        ),
        "accounting": (
            "{q} điều kiện đối tượng áp dụng",
            "{q} trường hợp ngoại lệ không bắt buộc",
            "{q} thời điểm hiệu lực và quy định chuyển tiếp",
        ),
    }
    return [clean_query(template.format(q=cleaned)) for template in templates.get(domain, ())]


def expand_query_for_retrieval(original_query: str, routing_query: str, domain: str) -> str:
    """Add only known canonical legal search terms; never alter the original text."""
    cleaned = clean_query(original_query)
    routing = normalize_for_routing(routing_query)
    additions: list[str] = []
    for normalized_phrase, *canonical_terms in _RETRIEVAL_EXPANSIONS.get(domain, ()):
        if normalized_phrase in routing:
            for term in canonical_terms:
                if term.casefold() not in cleaned.casefold() and term not in additions:
                    additions.append(term)
    return clean_query(" ".join([cleaned, *additions])) if additions else cleaned
