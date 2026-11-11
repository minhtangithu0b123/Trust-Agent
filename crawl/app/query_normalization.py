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
            "xe mô tô",
        ),
        ("o to", "ô tô"),
        ("tai nan", "tai nạn giao thông"),
    ),
    "labor": (
        ("hop dong lao dong", "hợp đồng lao động"),
        ("nghi phep", "nghỉ hằng năm, nghỉ phép"),
        ("luong", "tiền lương"),
        ("bao hiem xa hoi", "bảo hiểm xã hội"),
        ("tai nan lao dong", "tai nạn lao động"),
    ),
    "accounting": (
        ("hoa don dien tu", "hóa đơn điện tử"),
        ("thue gia tri gia tang", "thuế giá trị gia tăng"),
        ("ke toan", "kế toán"),
        ("quyet toan thue", "quyết toán thuế"),
    ),
}


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
