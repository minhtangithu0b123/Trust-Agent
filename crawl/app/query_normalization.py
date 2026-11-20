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
    # Vietnamese "đ" does not decompose under NFD. Also tolerate the older
    # UTF-8-as-Latin-1 spelling present in some crawled records.
    folded = without_marks.replace("đ", "d").replace("Đ", "D").replace("Ä‘", "d")
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
    ("cho 2 nguoi", "chở theo 02 người", "Điều 7 Khoản 2 điểm g"),
    ("cho theo 2 nguoi", "chở theo 02 người", "Điều 7 Khoản 2 điểm g"),
    ("cho qua so nguoi", "chở quá số người quy định", "Điều 7"),
    ("dien thoai", "sử dụng điện thoại khi điều khiển xe", "Điều 7 Khoản 4 điểm đ"),
    ("toc do", "vượt quá tốc độ", "giới hạn tốc độ"),
    ("10 20 km h", "vượt quá tốc độ từ 10 km/h đến 20 km/h"),
    ("025 04 mg l", "nồng độ cồn từ 0,25 đến 0,4 mg/l khí thở"),
    ("0,4 mg/lit", "nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở", "Điều 7 Khoản 9"),
    ("0.4 mg/lit", "nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở", "Điều 7 Khoản 9"),
    ("04 mg lit", "nồng độ cồn vượt quá 0,4 miligam/1 lít khí thở", "Điều 7 Khoản 9"),
)

_RETRIEVAL_EXPANSIONS["labor"] = _RETRIEVAL_EXPANSIONS["labor"] + (
    ("nghi viec", "chấm dứt hợp đồng lao động", "đơn phương chấm dứt hợp đồng", "thời hạn báo trước"),
    ("bao truoc", "thời hạn báo trước", "Điều 35 Bộ luật Lao động"),
    ("don phuong cham dut", "đơn phương chấm dứt hợp đồng", "thời hạn báo trước"),
    ("mang thai", "lao động nữ mang thai", "sa thải", "đơn phương chấm dứt hợp đồng"),
    ("nhieu hop dong", "người lao động giao kết nhiều hợp đồng", "BHXH theo hợp đồng giao kết đầu tiên", "bảo hiểm tai nạn lao động theo từng hợp đồng"),
)

_RETRIEVAL_EXPANSIONS["accounting"] = _RETRIEVAL_EXPANSIONS["accounting"] + (
    ("doanh thu", "doanh thu hằng năm", "ngưỡng doanh thu", "hộ kinh doanh, cá nhân kinh doanh"),
    ("800 trieu", "800.000.000 đồng", "doanh thu hằng năm", "nghĩa vụ thuế giá trị gia tăng", "thuế thu nhập cá nhân"),
    ("800000000", "800.000.000 đồng", "ngưỡng doanh thu hộ kinh doanh"),
    ("ban hang online", "kinh doanh thương mại điện tử", "nền tảng thương mại điện tử", "khấu trừ, khai thay và nộp thay thuế"),
    ("shopee", "sàn thương mại điện tử", "hộ kinh doanh, cá nhân kinh doanh", "khấu trừ và nộp thay thuế"),
    ("tiktok shop", "sàn thương mại điện tử", "nền tảng thương mại điện tử", "khấu trừ và nộp thay thuế"),
    ("freelancer", "thu nhập từ tiền lương, tiền công", "thu nhập từ kinh doanh", "khấu trừ thuế thu nhập cá nhân"),
)

_RETRIEVAL_EXPANSIONS["accounting"] = _RETRIEVAL_EXPANSIONS["accounting"] + (
    ("kiem tra thue", "ki\u1ec3m tra thu\u1ebf", "tr\u01b0\u1eddng h\u1ee3p ki\u1ec3m tra thu\u1ebf", "quy\u1ebft \u0111\u1ecbnh ki\u1ec3m tra thu\u1ebf"),
    ("cuong che", "c\u01b0\u1ee1ng ch\u1ebf thi h\u00e0nh quy\u1ebft \u0111\u1ecbnh h\u00e0nh ch\u00ednh v\u1ec1 thu\u1ebf"),
    ("hoan thue", "ho\u00e0n thu\u1ebf gi\u00e1 tr\u1ecb gia t\u0103ng"),
    ("mien thue", "mi\u1ec5n thu\u1ebf, gi\u1ea3m thu\u1ebf"),
)

_RETRIEVAL_EXPANSIONS["traffic"] = _RETRIEVAL_EXPANSIONS["traffic"] + (
    ("guong chieu hau", "g\u01b0\u01a1ng chi\u1ebfu h\u1eadu b\u00ean tr\u00e1i", "thi\u1ebft b\u1ecb an to\u00e0n c\u1ee7a xe m\u00f4 t\u00f4"),
    ("phat nguoi", "x\u1eed ph\u1ea1t qua h\u00ecnh \u1ea3nh", "ch\u1ee7 ph\u01b0\u01a1ng ti\u1ec7n"),
    ("xe cap cuu", "xe \u0111\u01b0\u1ee3c quy\u1ec1n \u01b0u ti\u00ean", "nh\u01b0\u1eddng \u0111\u01b0\u1eddng"),
    ("tru het diem", "b\u1ecb tr\u1eeb h\u1ebft \u0111i\u1ec3m", "c\u1ea5p l\u1ea1i gi\u1ea5y ph\u00e9p l\u00e1i xe sau 6 th\u00e1ng"),
)

_RETRIEVAL_EXPANSIONS["labor"] = _RETRIEVAL_EXPANSIONS["labor"] + (
    ("tu choi lam them", "l\u00e0m th\u00eam gi\u1edd ph\u1ea3i c\u00f3 s\u1ef1 \u0111\u1ed3ng \u00fd", "ng\u01b0\u1eddi s\u1eed d\u1ee5ng lao \u0111\u1ed9ng kh\u00f4ng \u0111\u01b0\u1ee3c \u00e9p bu\u1ed9c"),
    ("hop dong lao dong het han", "trong 30 ng\u00e0y k\u1ec3 t\u1eeb ng\u00e0y h\u1ebft h\u1ea1n", "h\u1ee3p \u0111\u1ed3ng lao \u0111\u1ed9ng chuy\u1ec3n th\u00e0nh kh\u00f4ng x\u00e1c \u0111\u1ecbnh th\u1eddi h\u1ea1n"),
    ("dieu chuyen", "t\u1ea1m th\u1eddi chuy\u1ec3n ng\u01b0\u1eddi lao \u0111\u1ed9ng l\u00e0m c\u00f4ng vi\u1ec7c kh\u00e1c", "gi\u1eef nguy\u00ean m\u1ee9c l\u01b0\u01a1ng"),
    ("kpi", "th\u01b0\u1eddng xuy\u00ean kh\u00f4ng ho\u00e0n th\u00e0nh c\u00f4ng vi\u1ec7c", "sa th\u1ea3i"),
    ("cong tac vien", "h\u1ee3p \u0111\u1ed3ng lao \u0111\u1ed9ng", "b\u1ea3o hi\u1ec3m x\u00e3 h\u1ed9i"),
)

_RETRIEVAL_EXPANSIONS["accounting"] = _RETRIEVAL_EXPANSIONS["accounting"] + (
    ("trung thuong", "thu nh\u1eadp t\u1eeb tr\u00fang th\u01b0\u1edfng", "tr\u00fang th\u01b0\u1edfng x\u1ed5 s\u1ed1", "v\u01b0\u1ee3t tr\u00ean 20 tri\u1ec7u \u0111\u1ed3ng", "thu\u1ebf su\u1ea5t 10%"),
    ("thuong tet", "ti\u1ec1n th\u01b0\u1edfng", "thu nh\u1eadp t\u1eeb ti\u1ec1n l\u01b0\u01a1ng, ti\u1ec1n c\u00f4ng"),
    ("luong thang 13", "ti\u1ec1n l\u01b0\u01a1ng, ti\u1ec1n th\u01b0\u1edfng", "thu nh\u1eadp ch\u1ecbu thu\u1ebf"),
    ("cho thue nha", "cho thu\u00ea t\u00e0i s\u1ea3n", "doanh thu cho thu\u00ea nh\u00e0", "thu\u1ebf su\u1ea5t"),
    ("youtube", "thu nh\u1eadp t\u1eeb qu\u1ea3ng c\u00e1o", "n\u1ec1n t\u1ea3ng s\u1ed1", "thu nh\u1eadp t\u1eeb kinh doanh"),
    ("google", "doanh thu qu\u1ea3ng c\u00e1o", "thu nh\u1eadp t\u1eeb kinh doanh", "kh\u1ea5u tr\u1eeb thu\u1ebf"),
)

_RETRIEVAL_EXPANSIONS["traffic"] = _RETRIEVAL_EXPANSIONS["traffic"] + (
    ("qua toc do", "v\u01b0\u1ee3t qu\u00e1 t\u1ed1c \u0111\u1ed9", "15 km/h"),
    ("tu choi kiem tra nong do con", "ki\u1ec3m tra n\u1ed3ng \u0111\u1ed9 c\u1ed3n", "kh\u00f4ng ch\u1ea5p h\u00e0nh y\u00eau c\u1ea7u ki\u1ec3m tra"),
    ("ban xe may chua sang ten", "chuy\u1ec3n quy\u1ec1n s\u1edf h\u1eefu ph\u01b0\u01a1ng ti\u1ec7n", "ch\u01b0a l\u00e0m th\u1ee7 t\u1ee5c sang t\u00ean"),
)

_RETRIEVAL_EXPANSIONS["labor"] = _RETRIEVAL_EXPANSIONS["labor"] + (
    ("ngay phep nam chua su dung", "ngh\u1ec9 h\u1eb1ng n\u0103m ch\u01b0a ngh\u1ec9", "thanh to\u00e1n ti\u1ec1n l\u01b0\u01a1ng nh\u1eefng ng\u00e0y ch\u01b0a ngh\u1ec9"),
    ("di lam muon", "ph\u1ea1t ti\u1ec1n, c\u1eaft l\u01b0\u01a1ng", "h\u00e0nh vi b\u1ecb nghi\u00eam c\u1ea5m khi x\u1eed l\u00fd k\u1ef7 lu\u1eadt"),
    ("duong tu nha den cong ty", "tai n\u1ea1n tr\u00ean tuy\u1ebfn \u0111\u01b0\u1eddng h\u1ee3p l\u00fd", "tai n\u1ea1n lao \u0111\u1ed9ng"),
)

_RETRIEVAL_EXPANSIONS["accounting"] = _RETRIEVAL_EXPANSIONS["accounting"] + (
    ("lai gui tiet kiem", "l\u00e3i ti\u1ec1n g\u1eedi", "thu nh\u1eadp \u0111\u01b0\u1ee3c mi\u1ec5n thu\u1ebf"),
    ("tang nha cho con", "t\u1eb7ng cho b\u1ea5t \u0111\u1ed9ng s\u1ea3n", "thu nh\u1eadp t\u1eeb qu\u00e0 t\u1eb7ng"),
    ("ke khai bo sung", "khai b\u1ed5 sung h\u1ed3 s\u01a1 khai thu\u1ebf", "khai sai d\u1eabn \u0111\u1ebfn thi\u1ebfu thu\u1ebf", "m\u1ee9c ph\u1ea1t"),
)

_RETRIEVAL_EXPANSIONS["traffic"] = _RETRIEVAL_EXPANSIONS["traffic"] + (
    ("via he", "v\u1ec9a h\u00e8", "l\u00f2ng \u0111\u01b0\u1eddng", "x\u1eed ph\u1ea1t"),
    ("nguoi ngoi sau", "ng\u01b0\u1eddi ng\u1ed3i sau xe m\u00f4 t\u00f4", "kh\u00f4ng \u0111\u1ed9i m\u0169 b\u1ea3o hi\u1ec3m"),
    ("khong co giay phep lai xe muon o to", "giao xe cho ng\u01b0\u1eddi kh\u00f4ng \u0111\u1ee7 \u0111i\u1ec1u ki\u1ec7n", "ch\u1ee7 ph\u01b0\u01a1ng ti\u1ec7n"),
)

_RETRIEVAL_EXPANSIONS["labor"] = _RETRIEVAL_EXPANSIONS["labor"] + (
    ("ngay le", "ng\u00e0y ngh\u1ec9 l\u1ec5, t\u1ebft", "ti\u1ec1n l\u01b0\u01a1ng l\u00e0m th\u00eam gi\u1edd \u00edt nh\u1ea5t b\u1eb1ng 300%"),
    ("thai san", "ngh\u1ec9 thai s\u1ea3n", "h\u1ee3p \u0111\u1ed3ng lao \u0111\u1ed9ng h\u1ebft h\u1ea1n", "\u0110i\u1ec1u 137"),
    ("dat coc", "c\u1ea5m ng\u01b0\u1eddi s\u1eed d\u1ee5ng lao \u0111\u1ed9ng gi\u1eef ti\u1ec1n", "\u0111\u1eb7t c\u1ecdc khi giao k\u1ebft h\u1ee3p \u0111\u1ed3ng lao \u0111\u1ed9ng"),
    ("nguoi lao dong nuoc ngoai", "ng\u01b0\u1eddi lao \u0111\u1ed9ng n\u01b0\u1edbc ngo\u00e0i", "gi\u1ea5y ph\u00e9p lao \u0111\u1ed9ng", "\u0110i\u1ec1u 151", "\u0110i\u1ec1u 152"),
)

_RETRIEVAL_EXPANSIONS["accounting"] = _RETRIEVAL_EXPANSIONS["accounting"] + (
    ("cham nop", "ti\u1ec1n ch\u1eadm n\u1ed9p", "0,03% m\u1ed7i ng\u00e0y", "th\u1eddi h\u1ea1n n\u1ed9p thu\u1ebf"),
    ("ban o to", "chuy\u1ec3n nh\u01b0\u1ee3ng t\u00e0i s\u1ea3n", "thu nh\u1eadp t\u1eeb chuy\u1ec3n nh\u01b0\u1ee3ng"),
    ("khau tru toan bo", "\u0111i\u1ec1u ki\u1ec7n kh\u1ea5u tr\u1eeb thu\u1ebf gi\u00e1 tr\u1ecb gia t\u0103ng", "h\u00f3a \u0111\u01a1n, ch\u1ee9ng t\u1eeb"),
    ("lao dong nuoc ngoai", "thu nh\u1eadp ti\u1ec1n l\u01b0\u01a1ng, ti\u1ec1n c\u00f4ng", "kh\u1ea5u tr\u1eeb thu\u1ebf thu nh\u1eadp c\u00e1 nh\u00e2n", "ng\u01b0\u1eddi n\u01b0\u1edbc ngo\u00e0i l\u00e0m vi\u1ec7c t\u1ea1i Vi\u1ec7t Nam"),
)

_RETRIEVAL_EXPANSIONS["traffic"] = _RETRIEVAL_EXPANSIONS["traffic"] + (
    ("cao toc", "\u0111\u01b0\u1eddng cao t\u1ed1c", "xe m\u00f4 t\u00f4 kh\u00f4ng \u0111\u01b0\u1ee3c \u0111i v\u00e0o \u0111\u01b0\u1eddng cao t\u1ed1c"),
    ("dung do", "d\u1eebng xe, \u0111\u1ed7 xe", "n\u01a1i c\u1ea5m d\u1eebng, c\u1ea5m \u0111\u1ed7", "c\u1ed5ng b\u1ec7nh vi\u1ec7n"),
    ("roi khoi hien truong", "r\u1eddi kh\u1ecfi hi\u1ec7n tr\u01b0\u1eddng tai n\u1ea1n", "b\u1ecf tr\u1ed1n sau tai n\u1ea1n giao th\u00f4ng", "ngh\u0129a v\u1ee5 c\u1ee9u gi\u00fap"),
)

_RETRIEVAL_EXPANSIONS["labor"] = _RETRIEVAL_EXPANSIONS["labor"] + (
    ("thu viec toi da", "th\u1eddi gian th\u1eed vi\u1ec7c kh\u00f4ng qu\u00e1 60 ng\u00e0y", "c\u00f4ng vi\u1ec7c c\u1ea7n tr\u00ecnh \u0111\u1ed9 chuy\u00ean m\u00f4n k\u1ef9 thu\u1eadt t\u1eeb cao \u0111\u1eb3ng tr\u1edf l\u00ean"),
    ("ket hon", "kh\u00f4ng \u0111\01b0\u1ee3c sa th\u1ea3i ho\u1eb7c \u0111\u01a1n ph\u01b0\u01a1ng ch\u1ea5m d\u1ee9t v\u00ec l\u00fd do k\u1ebft h\u00f4n"),
    ("pha san", "ph\u00e1 s\u1ea3n", "th\u1ee9 t\u1ef1 ph\u00e2n chia t\u00e0i s\u1ea3n", "ti\u1ec1n l\u01b0\u01a1ng, tr\u1ee3 c\u1ea5p, b\u1ea3o hi\u1ec3m"),
    ("co phieu thay vi tien mat", "ti\u1ec1n l\u01b0\u01a1ng", "h\u00ecnh th\u1ee9c tr\u1ea3 l\u01b0\u01a1ng", "thu nh\u1eadp c\u1ee7a ng\u01b0\u1eddi lao \u0111\u1ed9ng"),
)

_RETRIEVAL_EXPANSIONS["accounting"] = _RETRIEVAL_EXPANSIONS["accounting"] + (
    ("phu cap an trua", "ph\u1ee5 c\u1ea5p \u0103n tr\u01b0a", "ti\u1ec1n \u0103n gi\u1eefa ca", "kho\u1ea3n thu nh\u1eadp kh\u00f4ng t\u00ednh thu\u1ebf"),
    ("xang xe", "ph\u1ee5 c\u1ea5p x\u0103ng xe", "kho\u1ea3n ph\u00fac l\u1ee3i", "thu nh\u1eadp ch\u1ecbu thu\u1ebf"),
    ("nhieu cua hang", "h\u1ed9 kinh doanh c\u00f3 nhi\u1ec1u \u0111\u1ecba \u0111i\u1ec3m kinh doanh", "k\u00ea khai thu\u1ebf theo \u0111\u1ecba b\u00e0n"),
    ("thue suat", "h\u00f3a \u0111\u01a1n sai thu\u1ebf su\u1ea5t", "l\u1eadp h\u00f3a \u0111\u01a1n \u0111i\u1ec1u ch\u1ec9nh", "khai b\u1ed5 sung"),
    ("co phieu", "thu nh\u1eadp t\u1eeb ti\u1ec1n l\u01b0\u01a1ng, ti\u1ec1n c\u00f4ng", "l\u1ee3i \u00edch b\u1eb1ng c\u1ed5 phi\u1ebfu", "thu\u1ebf thu nh\u1eadp c\u00e1 nh\u00e2n"),
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
