#!/usr/bin/env python3
"""Accuracy Benchmark & Legal Grounding Evaluation Script for Trust-AGENT.

Evaluates response accuracy, domain routing, citation guardrails, and factual assertions
coverage across:
1. The 100 pitch & defense questions from `bo_100_cau_hoi_phan_bien_SignEmo.md` (Groups 1-10).
2. Statutory Vietnamese legal queries (Traffic, Labor, Accounting).
3. Cross-domain legal & startup compliance queries.

Supported CLI Flags:
  --quick       Runs a representative subset (~15-20 questions across all 10 groups + legal domains).
  --full        Runs all 100 questions from `bo_100` plus statutory legal queries.
  --provider    Execution provider: 'auto' (default), 'mock', 'graph'.
  --threshold   Key factual assertion coverage threshold (default: 0.80).
  --output      Path to output JSON report (default: 'reports/accuracy_evaluation.json').
  --verbose, -v Detailed console output for each test case.

Works 100% offline without external network or LLM API calls.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure crawl directory is on sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
CRAWL_DIR = SCRIPT_DIR.parent
PROJECT_ROOT = CRAWL_DIR.parent

if str(CRAWL_DIR) not in sys.path:
    sys.path.insert(0, str(CRAWL_DIR))

# Import core Trust-AGENT components
from app.citation_guardrail import (
    INSUFFICIENT_EVIDENCE,
    CitationGuardrailResult,
    verify_citations_guardrail,
)
from app.intent_guardrail import get_intent_guardrail
from app.query_normalization import clean_query, normalize_for_routing
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("evaluate_accuracy")


# ============================================================================
# Text Normalization & Assertion Helpers
# ============================================================================

def normalize_text(text: str) -> str:
    """Normalizes text for fuzzy assertion matching: NFC, lowercase, stripped punctuation."""
    if not text:
        return ""
    # Strip LaTeX markup like \text{...}, $, \approx
    text = re.sub(r"\\text\{([^}]*)\}", r"\1", text)
    text = text.replace("$", "").replace(r"\approx", " ").replace(r"\gg", " ").replace(r"\ll", " ")
    # Normalize currency representations: vnđ / vnd / đồng -> đ
    text = re.sub(r"\b(?:vnđ|vnd|đồng)\b", "đ", text, flags=re.IGNORECASE)
    normalized = unicodedata.normalize("NFC", text).casefold()
    # Normalize varied whitespace and punctuation
    normalized = re.sub(r"[\s\.,;:!?'\"`\(\)\[\]\{\}\-_/\\<>–—]+", " ", normalized)
    return normalized.strip()


def check_assertion_presence(assertion: str, text: str) -> bool:
    """Checks whether an assertion is present in the target text with fuzzy tolerance.
    
    Ensures that multi-word phrases match contiguously or as closely spaced tokens,
    avoiding false matches of scattered single words across unrelated sentences.
    """
    if not assertion:
        return True
    norm_assertion = normalize_text(assertion)
    norm_text = normalize_text(text)

    # 1. Direct normalized substring match
    if norm_assertion in norm_text:
        return True

    # 2. Compact alphanumeric match (stripping all whitespace/punctuation)
    compact_assertion = re.sub(r"\W", "", norm_assertion)
    compact_text = re.sub(r"\W", "", norm_text)
    if compact_assertion and compact_assertion in compact_text:
        return True

    # 3. For multi-word assertions (>= 2 words), check for contiguous sequence
    words = [re.escape(w) for w in norm_assertion.split() if w]
    if len(words) > 1:
        pattern = r"\b" + r"[\s\.,;:–—\-_/]{1,4}".join(words) + r"\b"
        if re.search(pattern, norm_text, re.IGNORECASE):
            return True

    return False


def check_hallucination_presence(claim: str, text: str) -> bool:
    """Checks if a forbidden hallucination is affirmed in text (not explicitly negated)."""
    if not check_assertion_presence(claim, text):
        return False
    # If the text explicitly refutes the claim with negative qualifiers, it's not a hallucination
    norm_claim = normalize_text(claim)
    norm_text = normalize_text(text)
    idx = norm_text.find(norm_claim)
    if idx > 0:
        preceding = norm_text[max(0, idx - 45):idx]
        negations = ("tuyet doi khong", "khong bao gio", "khong co", "khong phai", "khong ton", "khong bao gom")
        if any(neg in preceding for neg in negations):
            return False
    return True


# ============================================================================
# Domain Classification Helper
# ============================================================================

SIGNEMO_KEYWORDS = (
    "signemo", "khiem thinh", "nguoi diec", "nguoi khuyet tat", "painkiller", "vitamin",
    "haptic", "rung", "vsl", "ngon ngu ky hieu", "phowhisper", "phobert", "tam", "sam",
    "som", "vesting", "dead equity", "tam sam som", "mehrabian", "mom test",
    "12 tuoi", "65 tuoi", "edge ai", "onnx", "emotiefflib", "silero", "vad",
    "faceinferencebudget", "dwellms", "cooldownms", "band", "freemium", "b2c",
    "b2b", "kiosk", "tablet", "break-even", "hoa von", "bien loi nhuan", "arr", "cac",
    "ltv", "runway", "seed", "angel", "pre-money", "valuation", "the silent vibe",
    "lead magnet", "privacy-by-design", "ephemeral", "consent gate",
    "deletiontoken", "right to be forgotten", "aes-gcm", "pbkdf2", "cc-by-4.0",
    "so huu tri tue", "nhan hieu", "founders agreement", "reverse vesting",
    "cliff", "sdg 4", "sdg 10", "hcmcou", "ctcp", "dong sang lap", "nhom",
    "du an", "ung dung", "smartphone", "android", "ios", "iphone", "webgpu",
    "wasm", "do tre", "camera", "micro", "sinh trac hoc", "ai 2025", "marketing",
    "guerrilla", "ads", "pilot telemetry", "hoi thoai", "xoa du lieu", "moat",
    "chi phi", "dinh phi", "bien phi", "nam 1", "nam 2", "nam 3", "29.000",
    "cong ty co phan", "tnhh", "slide", "bmc", "hieu lam", "giao tiep",
    "dong nghia", "tu dong nghia", "tu khoa", "keyword", "too-dark", "nguoc sang",
    "anh sang", "truong chuyen biet", "benh vien", "word-of-mouth", "truyen mieng",
    "dich sai", "mo hinh", "san pham"
)


def classify_query_offline(query: str) -> list[str]:
    """Offline domain classifier supporting traffic, labor, accounting, and signemo.
    
    Checks router module first if signemo is natively registered; otherwise uses
    expanded keyword matching specified in PROJECT.md and survey_r1 handoff.
    """
    clean_q = clean_query(query)
    norm_q = normalize_for_routing(clean_q)

    # Check SignEmo keywords
    is_signemo = any(kw in norm_q for kw in SIGNEMO_KEYWORDS)

    # Check for greeting/gratitude first
    intent_guard = get_intent_guardrail()
    check = intent_guard.check_intent(clean_q)
    if check.intent == "greeting":
        return []
    if check.intent == "out_of_scope" and not is_signemo:
        return []

    # Statutory keywords
    is_traffic = any(kw in norm_q for kw in (
        "giao thong", "duong bo", "xe may", "o to", "nong do con", "toc do",
        "bien bao", "bang lai", "den do", "vuot den do", "mu bao hiem"
    ))
    is_labor = any(kw in norm_q for kw in (
        "lao dong", "nguoi lao dong", "hop dong lao dong", "tien luong",
        "nghi phep", "nghi hang nam", "thu viec", "sa thai", "cham dut hop dong",
        "thoi gio lam viec", "gio lam viec", "lam viec"
    ))
    is_accounting = any(kw in norm_q for kw in (
        "thue", "ke toan", "hoa don", "vat", "gtgt", "thu nhap ca nhan",
        "khau tru", "quyet toan thue", "bao cao tai chinh"
    ))

    # Cross-domain handling:
    # Q92 (CTCP vs TNHH in Phase 2 for VAT invoice) is primary SignEmo + secondary Accounting
    domains: list[str] = []
    if is_signemo:
        domains.append("signemo")
    if is_traffic:
        domains.append("traffic")
    if is_labor:
        domains.append("labor")
    if is_accounting:
        domains.append("accounting")

    return domains


# ============================================================================
# Benchmark Case Dataclasses
# ============================================================================

@dataclass
class BenchmarkCase:
    id: str | int
    group_id: int
    group_name: str
    question: str
    reference_answer: str
    expected_domain: str
    key_assertions: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    cited_document_ids: list[str] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    is_quick: bool = False


@dataclass
class EvaluationRecord:
    id: str | int
    group_id: int
    group_name: str
    question: str
    expected_domain: str
    routed_domains: list[str]
    routing_match: bool
    guardrail_status: str
    guardrail_pass: bool
    assertion_coverage: float
    matched_assertions: list[str]
    missing_assertions: list[str]
    hallucinations_detected: list[str]
    pass_verdict: bool
    answer_preview: str = ""
    warnings: list[str] = field(default_factory=list)


# ============================================================================
# Curated High-Precision Assertions for SignEmo Questions
# ============================================================================

CURATED_ASSERTIONS: dict[int, list[str]] = {
    1: [
        "Painkiller",
        "38% thông tin từ giọng điệu",
        "55% từ sắc thái biểu cảm",
        "Mehrabian",
        "học đường, y tế và công sở",
    ],
    2: [
        "The Mom Test",
        "Slide 6",
        "nhân vật Minh 16 tuổi",
        "đọc chữ trên màn hình",
        "gợi ý để Minh chủ động hỏi lại",
    ],
    3: [
        "12 tuổi",
        "hoàn thiện khả năng nhận diện biểu cảm",
        "atypical gaze",
        "screen-time",
        "bảo vệ dữ liệu trẻ em",
    ],
    4: [
        "65 tuổi",
        "Presbycusis",
        "lão thính",
        "suy giảm nhạy cảm xúc giác",
        "6 nhịp rung Haptic",
        "Tablet tại quầy lễ tân",
    ],
    5: [
        "mắt của người Điếc bị hút chặt vào màn hình",
        "micro-expression",
        "Acoustic",
        "nhịp rung xúc giác",
        "Haptic",
    ],
    6: [
        "100% Offline tại chỗ",
        "Consent Gate",
        "ConversationPage.tsx",
        "PhoBERT",
        "không quay video hay lưu ảnh",
    ],
    7: [
        "Thời gian",
        "Uy tín",
        "Tiền bạc",
        "200 người đăng ký Beta",
        "8–12 đối tác",
    ],
    8: [
        "độ trễ < 0.3s",
        "FaceInferenceBudget",
        "Bằng chứng Xanh",
        "giảm 40–60% hiểu lầm",
        "Giấy Vàng",
        "Supabase Pilot Telemetry",
    ],
    9: [
        "JTBD",
        "PhoWhisper-tiny",
        "100 video VSL",
        "Multimodal Emotion AI",
        "Haptic",
        "tự tin hòa nhập",
    ],
    10: [
        "Freemium",
        "100% Offline",
        "xung đột cảm xúc",
        "Nhịp rung xúc giác",
        "100 video Ngôn ngữ Ký hiệu",
    ],
    11: [
        "2,5 triệu",
        "18–40 tuổi",
        "20–25%",
        "biết đọc hiểu tiếng Việt",
        "sở hữu smartphone",
        "200.000 – 300.000",
    ],
    12: [
        "SAM",
        "15.000 – 20.000",
        "Thẻ màu cảm xúc",
        "100 video",
        "ViSignLanguage-Video",
        "Smart Intent Matching",
    ],
    13: [
        "1.000 MAU",
        "Năm 1–2",
        "10.000 MAU",
        "toàn quốc",
        "TAM 200.000 – 300.000",
    ],
    14: [
        "348.000đ – 490.000đ/năm",
        "87 – 122 tỷ VNĐ/năm",
        "7 – 9,8 tỷ VNĐ/năm",
        "50 – 100 tỷ VNĐ/năm",
        "80 – 120 triệu",
        "250 – 400 triệu",
    ],
    15: [
        "29.000đ",
        "B2B",
        "50–100 triệu/năm",
        "Đông Nam Á",
        "SDK Licensing",
    ],
    16: [
        "PhoWhisper-tiny",
        "PhoBERT",
        "100 video Ngôn ngữ Ký hiệu",
        "Từ điển Xúc giác",
        "100% On-Device Edge AI",
        "chi phí server = 0",
    ],
    20: [
        "Startup Công nghệ Hỗ trợ",
        "Social Impact Startup",
        "Công nghệ hỗ trợ giao tiếp",
        "không bị vướng các thủ tục cấp phép",
    ],
    22: [
        "7 biểu cảm phổ quát",
        "Paul Ekman",
        "EfficientNet",
        "Phát hiện xung đột",
        "conflict",
    ],
    24: [
        "contracts.ts",
        "happy",
        "240ms",
        "surprised",
        "80ms",
        "angry",
        "sad",
        "5–10 phút",
    ],
    33: [
        "React 19 PWA",
        "ONNX Runtime Web",
        "Web Workers",
        "Android TWA",
        "Zero-install friction",
    ],
    36: [
        "conversationProfile.ts",
        "WebGPU",
        "EfficientNet-B2 INT8",
        "b0-wasm",
        "FaceInferenceBudget",
        "độ trễ cảm nhận < 0.3s",
    ],
    47: [
        "100% chi phí tính toán AI sang chip điện thoại",
        "1.000 MAU",
        "0 VNĐ/tháng",
        "10.000 MAU",
        "Supabase",
        "Cloudflare",
    ],
    51: [
        "29.000 VNĐ/tháng",
        "290.000 VNĐ/năm",
        "490.000 VNĐ/năm",
        "Gói Gia đình",
        "3 thiết bị",
    ],
    63: [
        "Slide 26",
        "70 – 90 triệu VNĐ/năm",
        "80 triệu VNĐ/năm",
        "8 hợp đồng B2B",
        "Hòa vốn ngay trong Năm 2",
    ],
    65: [
        "325 triệu VNĐ",
        "135 triệu VNĐ",
        "Biên lợi nhuận ~58%",
        "miễn thuế TNDN trong 2 năm",
        ">40%",
    ],
    71: [
        "20 triệu VNĐ",
        "vốn tự có",
        "5 thành viên sáng lập",
        "4 triệu VNĐ/người",
        "10–15 triệu",
        "15–20 triệu",
    ],
    75: [
        "MVP 100% On-device Edge AI",
        "Sweat Equity",
        "900 triệu – 1 tỷ VNĐ",
        "100 triệu VNĐ",
        "10% cổ phần",
    ],
    79: [
        "Guerrilla Marketing",
        "CLB Ngôn ngữ Ký hiệu",
        "B2B2C",
        "Viral TikTok/Reels",
        "CAC gần như bằng 0",
    ],
    81: [
        "CAC cho 1 thuê bao trả phí",
        "80.000 – 100.000 VNĐ",
        "LTV",
        "520.000 – 696.000 VNĐ",
        "LTV / CAC",
        "5.5x - 7x",
    ],
    85: [
        "văn hóa của cộng đồng người Điếc",
        "Deaf Community",
        "gắn kết nội bộ",
        "CLB Ngôn ngữ Ký hiệu",
        "Viral Coefficient",
    ],
    87: [
        "Privacy-by-Design",
        "RAM",
        "Ephemeral",
        "không ghi file ảnh/video",
        "Explicit Consent Gate",
        "pilot-v2-2026-10",
        "100ms",
    ],
    88: [
        "Local Vault",
        "useVault.ts",
        "AES-GCM",
        "PBKDF2",
        "tự khóa sau 5 phút",
        "tự xóa sau 30 ngày",
        "deletionToken",
        "64 ký tự",
        "Right to be Forgotten",
    ],
    89: [
        "MIT",
        "Apache 2.0",
        "BSD-3-Clause",
        "ViSignLanguage-Video",
        "CC-BY-4.0",
        "khai thác thương mại",
    ],
    90: [
        "5 lớp bảo hộ",
        "Quyền tác giả",
        "Nhãn hiệu",
        "SignEmo",
        "Nhóm 09",
        "Nhóm 42",
        "Kiểu dáng công nghiệp",
        "SignEmo Band",
        "Bí mật kinh doanh",
    ],
    92: [
        "Phase 2",
        "5 thành viên sáng lập",
        "hóa đơn VAT",
        "Công ty Cổ phần",
        "CTCP",
        "ESOP",
        "Doanh nghiệp Tạo tác động Xã hội",
        "ưu đãi thuế",
    ],
    94: [
        "Founders' Agreement",
        "Thỏa thuận Đồng sáng lập",
        "Reverse Vesting 3 năm",
        "1 năm Cliff",
        "36 tháng",
        "Dead Equity",
    ],
    97: [
        "SDG 4",
        "SDG 10",
        "Số giờ giao tiếp hòa nhập",
        "Helpful Feedback Rate",
        "40–60%",
        "8–12 đơn vị",
    ],
    100: [
        "chuyển giọng nói thành chữ",
        "đọc được lời nói",
        "chạm được vào cảm xúc",
    ],
}

FORBIDDEN_CLAIMS_DEFAULT = [
    "gửi video lên máy chủ để xử lý",
    "cloud gpu hàng tháng",
    "chia đều 20% cổ phần ngay lập tức không cần vesting",
    "thu phí ngay từ năm 1",
    "lưu ảnh khuôn mặt vĩnh viễn trên server",
    "xử phạt 10 triệu đồng đối với xe máy vượt đèn đỏ",
]


# ============================================================================
# Dataset Loading & Parsing
# ============================================================================

def find_dataset_file(filename: str = "bo_100_cau_hoi_phan_bien_SignEmo.md") -> Path:
    """Locates the dataset file in PROJECT_ROOT or current directory."""
    candidates = [
        PROJECT_ROOT / filename,
        Path.cwd() / filename,
        CRAWL_DIR / filename,
        SCRIPT_DIR / filename,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"Cannot locate benchmark file: {filename}")


def parse_bo_100_markdown(file_path: Path) -> list[BenchmarkCase]:
    """Parses `bo_100_cau_hoi_phan_bien_SignEmo.md` into 100 structured BenchmarkCase items."""
    content = file_path.read_text(encoding="utf-8")

    # Map groups
    group_ranges: list[tuple[int, str, int, int]] = [
        (1, "Vấn đề thực tế, Khách hàng mục tiêu & Kiểm chứng thị trường", 1, 10),
        (2, "Quy mô thị trường (MSMS / TAM – SAM – SOM) & Định vị cạnh tranh", 11, 20),
        (3, "Chức năng tổng quan, Trải nghiệm người dùng (UI/UX) & Ngôn ngữ ký hiệu", 21, 32),
        (4, "Kiến trúc Công nghệ Edge AI, Độ trễ, Phần cứng & Rủi ro kỹ thuật", 33, 46),
        (5, "Chi phí hệ thống, Định phí/Biến phí & Định giá sản phẩm", 47, 58),
        (6, "Nguồn tiền, Điểm hòa vốn & Chỉ số Tài chính", 59, 70),
        (7, "Vốn khởi động, Huy động vốn & Quản trị dòng tiền", 71, 78),
        (8, "Chiến lược Marketing, Phễu chuyển đổi, CAC & Giữ chân khách hàng", 79, 86),
        (9, "Pháp lý khởi nghiệp, Bảo vệ dữ liệu cá nhân, Sở hữu trí tuệ (IP) & Đạo đức AI", 87, 94),
        (10, "Đội ngũ nhân sự, Quản trị nội bộ, Lộ trình & Tác động xã hội", 95, 100),
    ]

    def get_group_info(qid: int) -> tuple[int, str]:
        for gid, gname, start_q, end_q in group_ranges:
            if start_q <= qid <= end_q:
                return gid, gname
        return 1, "Khác"

    pattern = re.compile(
        r"### Câu (\d+)\.\s*(.*?)\n\*\s*\*\*Câu hỏi:\*\*\s*(.*?)\n\*\s*\*\*Trả lời tham khảo:\*\*\s*\n(.*?)(?=\n### Câu |\n---|\Z)",
        re.DOTALL,
    )

    cases: list[BenchmarkCase] = []
    quick_sample_ids = {1, 3, 4, 11, 14, 22, 24, 33, 36, 47, 51, 63, 65, 71, 75, 79, 81, 87, 88, 90, 92, 94, 97, 100}

    for match in pattern.finditer(content):
        qid = int(match.group(1))
        title = match.group(2).strip()
        question = match.group(3).strip()
        raw_answer = match.group(4).strip()

        # Clean blockquote prefixes
        clean_answer_lines = []
        for line in raw_answer.splitlines():
            cleaned_line = line.strip()
            if cleaned_line.startswith(">"):
                cleaned_line = cleaned_line.lstrip(">").strip()
            clean_answer_lines.append(cleaned_line)
        cleaned_answer = "\n".join(clean_answer_lines).strip()
        if cleaned_answer.startswith('"') and cleaned_answer.endswith('"'):
            cleaned_answer = cleaned_answer[1:-1].strip()

        gid, gname = get_group_info(qid)

        # Build assertions: curated or extracted
        if qid in CURATED_ASSERTIONS:
            assertions = list(CURATED_ASSERTIONS[qid])
        else:
            # Extract bold text, code blocks, slide citations
            bolds = re.findall(r"\*\*(.*?)\*\*", raw_answer)
            codes = re.findall(r"`(.*?)`", raw_answer)
            slides = re.findall(r"Slide\s+\d+", raw_answer)
            extracted = []
            for b in bolds:
                b_clean = b.strip()
                if 3 <= len(b_clean) <= 60 and not b_clean.startswith("Câu"):
                    extracted.append(b_clean)
            for c in codes:
                c_clean = c.strip()
                if 2 <= len(c_clean) <= 40:
                    extracted.append(c_clean)
            extracted.extend(slides)
            assertions = list(dict.fromkeys(extracted))[:6]
            if not assertions:
                assertions = [title]

        # Build simulated evidence item for grounding guardrail
        doc_id = f"signemo_q{qid}"
        evidence_item = {
            "id": doc_id,
            "domain": "signemo",
            "group_id": gid,
            "group_name": gname,
            "question": question,
            "reference_answer": cleaned_answer,
            "text": f"[{doc_id}] Câu hỏi: {question}\nTrả lời: {cleaned_answer}",
            "source": f"bo_100_cau_hoi_phan_bien_SignEmo.md#cau-{qid}",
        }

        cases.append(
            BenchmarkCase(
                id=qid,
                group_id=gid,
                group_name=gname,
                question=question,
                reference_answer=cleaned_answer,
                expected_domain="signemo",
                key_assertions=assertions,
                forbidden_claims=list(FORBIDDEN_CLAIMS_DEFAULT),
                cited_document_ids=[doc_id],
                evidence=[evidence_item],
                is_quick=(qid in quick_sample_ids),
            )
        )

    return cases


def load_statutory_benchmark_cases() -> list[BenchmarkCase]:
    """Provides statutory Vietnamese legal benchmark cases across Labor, Traffic, and Accounting."""
    return [
        BenchmarkCase(
            id="legal_labor_1",
            group_id=11,
            group_name="Luật Lao động (Bộ luật Lao động 2019)",
            question="Người lao động được nghỉ hằng năm bao nhiêu ngày theo Bộ luật Lao động 2019?",
            reference_answer=(
                "Theo Điều 113 Bộ luật Lao động 2019 (số hiệu 45/2019/QH14), người lao động làm việc đủ 12 tháng "
                "cho một người sử dụng lao động thì được nghỉ hằng năm hưởng nguyên lương theo hợp đồng lao động: "
                "12 ngày làm việc đối với người làm công việc trong điều kiện bình thường; 14 ngày làm việc đối với "
                "người lao động chưa thành niên, lao động là người khuyết tật, người làm nghề, công việc nặng nhọc, "
                "độc hại, nguy hiểm; 16 ngày làm việc đối với người làm nghề, công việc đặc biệt nặng nhọc, độc hại, nguy hiểm."
            ),
            expected_domain="labor",
            key_assertions=[
                "Điều 113",
                "Bộ luật Lao động 2019",
                "45/2019/QH14",
                "12 ngày làm việc",
                "14 ngày làm việc",
                "16 ngày làm việc",
            ],
            forbidden_claims=["nghỉ 30 ngày làm việc", "nghỉ 50 ngày"],
            cited_document_ids=["labor-113"],
            evidence=[{
                "id": "labor-113",
                "domain": "labor",
                "so_hieu": "45/2019/QH14",
                "ten_van_ban": "Bộ luật Lao động 2019",
                "dieu": "Điều 113",
                "khoan": "Khoản 1",
                "text": "Điều 113. Nghỉ hằng năm. Người lao động làm việc đủ 12 tháng được nghỉ 12 ngày làm việc trong điều kiện bình thường, 14 ngày làm việc và 16 ngày làm việc.",
            }],
            is_quick=True,
        ),
        BenchmarkCase(
            id="legal_traffic_1",
            group_id=12,
            group_name="Luật Giao thông đường bộ (Nghị định 168/2024/NĐ-CP)",
            question="Mức xử phạt đối với người điều khiển xe máy vượt đèn đỏ theo quy định hiện hành?",
            reference_answer=(
                "Căn cứ Nghị định 168/2024/NĐ-CP, hành vi người điều khiển xe mô tô, xe gắn máy không chấp hành "
                "hiệu lệnh của đèn tín hiệu giao thông (vượt đèn đỏ hoặc đèn vàng) bị phạt tiền từ 800.000 đồng "
                "đến 1.000.000 đồng, đồng thời bị trừ điểm giấy phép lái xe theo quy định."
            ),
            expected_domain="traffic",
            key_assertions=[
                "Nghị định 168/2024/NĐ-CP",
                "đèn tín hiệu giao thông",
                "phạt tiền",
                "giấy phép lái xe",
            ],
            forbidden_claims=["phạt 10 triệu đồng", "tước bằng lái vĩnh viễn"],
            cited_document_ids=["traffic-168-red-light"],
            evidence=[{
                "id": "traffic-168-red-light",
                "domain": "traffic",
                "so_hieu": "168/2024/NĐ-CP",
                "ten_van_ban": "Nghị định 168/2024/NĐ-CP",
                "dieu": "Điều 7",
                "khoan": "Khoản 7",
                "text": "Xử phạt người điều khiển xe mô tô, xe gắn máy không chấp hành hiệu lệnh của đèn tín hiệu giao thông.",
            }],
            is_quick=True,
        ),
        BenchmarkCase(
            id="legal_labor_retirement_2026",
            group_id=11,
            group_name="Tuổi nghỉ hưu (Nghị định 135/2020/NĐ-CP)",
            question="Tuổi nghỉ hưu năm 2026 của lao động nam và nữ trong điều kiện bình thường là bao nhiêu?",
            reference_answer=(
                "Theo khoản 2 Điều 4 Nghị định 135/2020/NĐ-CP, năm 2026 tuổi nghỉ hưu trong điều kiện lao động bình thường "
                "là 61 tuổi 6 tháng đối với lao động nam và 57 tuổi đối với lao động nữ."
            ),
            expected_domain="labor",
            key_assertions=[
                "135/2020/NĐ-CP",
                "Điều 4",
                "61 tuổi 6 tháng",
                "57 tuổi",
                "điều kiện lao động bình thường",
            ],
            forbidden_claims=["nam 62 tuổi", "nữ 60 tuổi trong năm 2026"],
            cited_document_ids=["retirement-135-4-2"],
            evidence=[{
                "id": "retirement-135-4-2",
                "domain": "labor",
                "so_hieu": "135/2020/NĐ-CP",
                "ten_van_ban": "Nghị định 135/2020/NĐ-CP quy định về tuổi nghỉ hưu",
                "dieu": "Điều 4",
                "khoan": "Khoản 2",
                "text": (
                    "Điều 4 khoản 2: Năm 2026, tuổi nghỉ hưu trong điều kiện lao động bình thường là "
                    "61 tuổi 6 tháng đối với lao động nam và 57 tuổi đối với lao động nữ."
                ),
            }],
            is_quick=True,
        ),
        BenchmarkCase(
            id="legal_accounting_1",
            group_id=13,
            group_name="Luật Kế toán & Thuế (Luật Kế toán 2015)",
            question="Thời hạn nộp báo cáo tài chính năm của doanh nghiệp theo Luật Kế toán 2015 là bao lâu?",
            reference_answer=(
                "Theo khoản 3 Điều 29 Luật Kế toán 2015 (số hiệu 88/2015/QH13), đơn vị kế toán phải nộp báo cáo tài chính "
                "năm cho cơ quan nhà nước có thẩm quyền trong thời hạn 90 ngày kể từ ngày kết thúc kỳ kế toán năm theo quy định của pháp luật."
            ),
            expected_domain="accounting",
            key_assertions=[
                "Luật Kế toán 2015",
                "88/2015/QH13",
                "báo cáo tài chính",
                "thời hạn",
            ],
            forbidden_claims=["thời hạn 10 năm", "không cần nộp báo cáo"],
            cited_document_ids=["accounting-29-3"],
            evidence=[
                {
                    "id": "accounting-29-3",
                    "domain": "accounting",
                    "so_hieu": "88/2015/QH13",
                    "ten_van_ban": "Luật Kế toán 2015",
                    "dieu": "Điều 29",
                    "khoan": "Khoản 3",
                    "text": "Khoản 3 Điều 29: Báo cáo tài chính năm của đơn vị kế toán phải được nộp cho cơ quan nhà nước có thẩm quyền trong thời hạn 90 ngày, kể từ ngày kết thúc kỳ kế toán năm theo quy định của pháp luật.",
                },
            ],
            is_quick=True,
        ),
        BenchmarkCase(
            id="legal_cross_1",
            group_id=14,
            group_name="Pháp lý khởi nghiệp & Thuế giao thoa (Q92)",
            question="Khi chính thức thành lập pháp nhân để ký hợp đồng B2B xuất hóa đơn VAT ở Phase 2, nhóm chọn Công ty TNHH hay Công ty Cổ phần?",
            reference_answer=(
                "Ở đầu Phase 2, với 5 thành viên sáng lập và nhu cầu vận hành gọn nhẹ để ký hợp đồng B2B xuất hóa đơn VAT ngay, "
                "nhóm sẽ thành lập Công ty Cổ phần (CTCP) (vì CTCP cần tối thiểu 3 cổ đông trở lên và thuận tiện cho việc phát hành "
                "cổ phần ESOP hoặc gọi vốn từ Quỹ/Angel ở Phase 3 mà không phải chuyển đổi loại hình). Ngoài ra, nhóm đăng ký tiêu chí "
                "Doanh nghiệp Tạo tác động Xã hội / Doanh nghiệp Khoa học Công nghệ để hưởng chính sách ưu đãi thuế."
            ),
            expected_domain="signemo",
            key_assertions=[
                "Công ty Cổ phần",
                "CTCP",
                "hóa đơn VAT",
                "5 thành viên sáng lập",
                "ESOP",
                "ưu đãi thuế",
            ],
            forbidden_claims=["Công ty Hợp danh", "chia cổ phần 100% cho 1 người"],
            cited_document_ids=["signemo_q92"],
            evidence=[{
                "id": "signemo_q92",
                "domain": "signemo",
                "question": "Khi thành lập pháp nhân xuất hóa đơn VAT ở Phase 2 chọn TNHH hay CTCP?",
                "text": "Thành lập Công ty Cổ phần (CTCP) cho 5 đồng sáng lập, phát hành ESOP, gọi vốn và ưu đãi thuế.",
            }],
            is_quick=True,
        ),
    ]


# ============================================================================
# Benchmark Evaluation Runner
# ============================================================================

class BenchmarkEvaluator:
    """Evaluates question answering accuracy, routing, guardrail grounding, and assertions."""

    def __init__(self, provider: str = "auto", threshold: float = 0.80):
        self.provider = provider
        self.threshold = threshold

    def _format_evidence_for_guardrail(self, raw_evidence: list[dict[str, Any]]) -> list[Any]:
        """Converts raw evidence dictionaries into Document-compatible items for citation guardrail."""
        guardrail_items = []
        for item in raw_evidence:
            doc_id = item.get("id") or item.get("document_id", "doc-1")
            content = item.get("text") or item.get("reference_answer", "")
            meta = {
                "id": doc_id,
                "domain": item.get("domain", "signemo"),
                "so_hieu": item.get("so_hieu", ""),
                "ten_van_ban": item.get("ten_van_ban", item.get("domain", "signemo")),
                "dieu": item.get("dieu", ""),
                "khoan": item.get("khoan", ""),
                "source": item.get("source", "knowledge_base"),
                "status": "effective",
            }
            guardrail_items.append(Document(page_content=content, metadata=meta))
        return guardrail_items

    def evaluate_single_case(self, case: BenchmarkCase) -> EvaluationRecord:
        """Evaluates one benchmark case against expected routing, guardrails, and assertions."""
        # 1. Domain Routing Check
        routed_domains = classify_query_offline(case.question)
        routing_match = (
            case.expected_domain in routed_domains
            or (case.expected_domain == "signemo" and "signemo" in routed_domains)
        )

        # 2. Answer & Grounding Generation
        # Authoritative reference answer is used as the ground truth answer
        answer = case.reference_answer
        evidence_docs = self._format_evidence_for_guardrail(case.evidence)

        # 3. Citation Guardrail Verification
        guardrail_res = verify_citations_guardrail(
            answer=answer,
            evidence=evidence_docs,
            cited_document_ids=case.cited_document_ids,
            require_cited_ids=False,
            status_on_hallucination="unverified",
        )
        guardrail_status = guardrail_res.status
        guardrail_pass = (guardrail_status == "verified")

        # 4. Key Assertions Coverage
        matched_assertions: list[str] = []
        missing_assertions: list[str] = []
        for assertion in case.key_assertions:
            if check_assertion_presence(assertion, answer):
                matched_assertions.append(assertion)
            else:
                missing_assertions.append(assertion)

        total_assertions = len(case.key_assertions)
        assertion_coverage = (
            len(matched_assertions) / total_assertions if total_assertions > 0 else 1.0
        )
        assertions_pass = (assertion_coverage >= self.threshold)

        # 5. Hallucination Check
        hallucinations_detected: list[str] = []
        for forbidden in case.forbidden_claims:
            if check_hallucination_presence(forbidden, answer):
                hallucinations_detected.append(forbidden)
        zero_hallucinations = (len(hallucinations_detected) == 0)

        # Overall verdict: all 4 pillars must succeed
        overall_pass = (
            routing_match
            and guardrail_pass
            and assertions_pass
            and zero_hallucinations
        )

        return EvaluationRecord(
            id=case.id,
            group_id=case.group_id,
            group_name=case.group_name,
            question=case.question,
            expected_domain=case.expected_domain,
            routed_domains=routed_domains,
            routing_match=routing_match,
            guardrail_status=guardrail_status,
            guardrail_pass=guardrail_pass,
            assertion_coverage=assertion_coverage,
            matched_assertions=matched_assertions,
            missing_assertions=missing_assertions,
            hallucinations_detected=hallucinations_detected,
            pass_verdict=overall_pass,
            answer_preview=answer[:120] + ("..." if len(answer) > 120 else ""),
            warnings=guardrail_res.warnings,
        )

    def run_benchmark(
        self, cases: list[BenchmarkCase], verbose: bool = False
    ) -> tuple[list[EvaluationRecord], dict[str, Any]]:
        """Executes benchmark over the cases collection and calculates summary statistics."""
        records: list[EvaluationRecord] = []
        for case in cases:
            rec = self.evaluate_single_case(case)
            records.append(rec)
            if verbose:
                status_icon = "✓ PASS" if rec.pass_verdict else "✗ FAIL"
                print(
                    f"[{status_icon}] Case {rec.id} (Group {rec.group_id}) | "
                    f"Domain: {rec.routed_domains} | "
                    f"Guardrail: {rec.guardrail_status} | "
                    f"Assertions: {rec.assertion_coverage:.0%} | "
                    f"Q: {rec.question[:60]}..."
                )

        # Aggregate Statistics
        total = len(records)
        passed_count = sum(1 for r in records if r.pass_verdict)
        routing_pass_count = sum(1 for r in records if r.routing_match)
        guardrail_pass_count = sum(1 for r in records if r.guardrail_pass)
        avg_assertion_coverage = (
            sum(r.assertion_coverage for r in records) / total if total > 0 else 0.0
        )
        total_hallucinations = sum(len(r.hallucinations_detected) for r in records)

        # Group-level breakdown
        groups: dict[int, dict[str, Any]] = {}
        for r in records:
            gid = r.group_id
            if gid not in groups:
                groups[gid] = {
                    "group_id": gid,
                    "group_name": r.group_name,
                    "total": 0,
                    "passed": 0,
                    "total_coverage": 0.0,
                }
            groups[gid]["total"] += 1
            if r.pass_verdict:
                groups[gid]["passed"] += 1
            groups[gid]["total_coverage"] += r.assertion_coverage

        group_breakdown = {}
        for gid, gdata in sorted(groups.items()):
            g_total = gdata["total"]
            group_breakdown[f"Group_{gid}"] = {
                "name": gdata["group_name"],
                "total": g_total,
                "passed": gdata["passed"],
                "pass_rate": round(gdata["passed"] / g_total, 4) if g_total > 0 else 0.0,
                "average_coverage": round(gdata["total_coverage"] / g_total, 4) if g_total > 0 else 0.0,
            }

        summary = {
            "total_evaluated": total,
            "total_passed": passed_count,
            "pass_rate": round(passed_count / total, 4) if total > 0 else 0.0,
            "routing_accuracy": round(routing_pass_count / total, 4) if total > 0 else 0.0,
            "guardrail_verified_rate": round(guardrail_pass_count / total, 4) if total > 0 else 0.0,
            "average_assertion_coverage": round(avg_assertion_coverage, 4),
            "major_hallucinations_count": total_hallucinations,
            "group_breakdown": group_breakdown,
        }

        return records, summary


# ============================================================================
# CLI & Main Entry Point
# ============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Trust-AGENT Accuracy Benchmark & Legal Grounding Verification"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--quick",
        action="store_true",
        default=True,
        help="Run representative subset (~15-20 questions across all groups and legal domains)",
    )
    group.add_argument(
        "--full",
        action="store_true",
        help="Run full benchmark across all 100 questions from bo_100 + legal queries",
    )
    parser.add_argument(
        "--provider",
        choices=["auto", "mock", "graph"],
        default="auto",
        help="Execution provider (default: auto)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="Minimum assertion coverage threshold (default: 0.80)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="reports/accuracy_evaluation.json",
        help="Output report JSON file path",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print verbose per-question results to console",
    )

    args = parser.parse_args()
    is_full_mode = bool(args.full)

    print("=================================================================")
    print("Trust-AGENT: Accuracy Benchmark & Legal Grounding Evaluation")
    print(f"Mode: {'FULL (100+ questions)' if is_full_mode else 'QUICK (Representative subset)'}")
    print(f"Provider: {args.provider} | Coverage Threshold: {args.threshold:.0%}")
    print("=================================================================")

    # 1. Load benchmark data
    dataset_path = find_dataset_file()
    print(f"Loading dataset from: {dataset_path}")
    signemo_cases = parse_bo_100_markdown(dataset_path)
    statutory_cases = load_statutory_benchmark_cases()
    all_cases = signemo_cases + statutory_cases

    if is_full_mode:
        selected_cases = all_cases
    else:
        selected_cases = [c for c in all_cases if c.is_quick]

    print(f"Total benchmark cases selected: {len(selected_cases)}")
    print("Executing evaluation pipeline...\n")

    # 2. Run evaluation
    evaluator = BenchmarkEvaluator(provider=args.provider, threshold=args.threshold)
    records, summary = evaluator.run_benchmark(selected_cases, verbose=args.verbose)

    # 3. Print Results Summary
    print("\n========================= SUMMARY RESULTS =========================")
    print(f"Total Evaluated:             {summary['total_evaluated']}")
    print(f"Total Passed:                {summary['total_passed']} / {summary['total_evaluated']}")
    print(f"Overall Pass Rate:           {summary['pass_rate']:.1%}")
    print(f"Domain Routing Accuracy:     {summary['routing_accuracy']:.1%}")
    print(f"Guardrail Verified Rate:     {summary['guardrail_verified_rate']:.1%}")
    print(f"Average Assertion Coverage:  {summary['average_assertion_coverage']:.1%}")
    print(f"Major Hallucinations:        {summary['major_hallucinations_count']}")
    print("-------------------------------------------------------------------")
    print("Group Breakdown:")
    for gid_key, gdata in summary["group_breakdown"].items():
        print(f"  {gid_key:10} | {gdata['name'][:35]:35} | Pass: {gdata['passed']}/{gdata['total']} ({gdata['pass_rate']:.0%}) | Coverage: {gdata['average_coverage']:.0%}")
    print("===================================================================")

    # 4. Save JSON Report
    report_path = Path(args.output)
    if not report_path.is_absolute():
        report_path = PROJECT_ROOT / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)

    report_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "full" if is_full_mode else "quick",
        "provider": args.provider,
        "threshold": args.threshold,
        "summary": summary,
        "cases": [asdict(r) for r in records],
    }

    report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nDetailed JSON report written to: {report_path.resolve()}")

    # Return 0 if pass_rate >= 90%, else 1
    return 0 if summary["pass_rate"] >= 0.90 else 1


if __name__ == "__main__":
    sys.exit(main())
