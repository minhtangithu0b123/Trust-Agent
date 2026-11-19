"""Citation Verification Guardrail module for Trust-AGENT.

Extracts Vietnamese legal citations (document numbers, articles, clauses)
from generated answers, builds a Grounding Index from retrieval evidence,
and verifies citations against retrieved evidence to detect and prevent
hallucinations.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any

logger = logging.getLogger(__name__)

INSUFFICIENT_EVIDENCE = "Chưa đủ căn cứ từ dữ liệu hiện có để kết luận."


def _clean_nfc(text: Any) -> str:
    """Normalizes Unicode text to canonical NFC form."""
    if text is None:
        return ""
    return unicodedata.normalize("NFC", str(text))


# Regex patterns for Vietnamese legal citations
# 1. Số hiệu văn bản quy phạm pháp luật (Luật, Nghị định, Thông tư, Quyết định, VBHN, etc.)
# Examples: 45/2019/QH14, 36/2024/QH15, 168/2024/NĐ-CP, 35/2024/TT-BGTVT, 12/VBHN-BGTVT, 88/2015/QH13
SO_HIEU_PATTERN = re.compile(
    r"\b(\d+/(?:(?:19\d\d|20\d\d)/[A-Za-z0-9Đđ\-_]+|[A-Za-z0-9Đđ\-_]+-[A-Za-z0-9Đđ\-_]+))\b",
    re.IGNORECASE,
)

# 2. Điều luật: "Điều 6", "Điều 113", "Điều 32a", "Điều 32đ", "điều 15", "ĐIỀU 113", "ĐIỀU 32Đ"
DIEU_PATTERN = re.compile(
    r"\b(?:điều)\s+(\d+[a-zA-ZđĐ]*)\b",
    re.IGNORECASE,
)

# 3. Khoản: "Khoản 1", "khoản 2", "Khoản 11", "KHOẢN 1"
KHOAN_PATTERN = re.compile(
    r"\b(?:khoản)\s+(\d+)\b",
    re.IGNORECASE,
)

# 4. Điểm: "Điểm a", "điểm b"
DIEM_PATTERN = re.compile(
    r"\b(?:điểm)\s+([a-zđ])\b",
    re.IGNORECASE,
)


def contains_insufficient_evidence(answer: str) -> bool:
    """Checks whether the answer text contains the standard insufficient evidence phrase."""
    normalized = " ".join(_clean_nfc(answer).casefold().split()).rstrip(".")
    phrase = "chưa đủ căn cứ từ dữ liệu hiện có để kết luận"
    return phrase in normalized


QUANTITATIVE_PATTERN = re.compile(
    r"(?<!\w)(\d[\d.,]*)\s*(đồng|vnđ|vnd|ngày|tháng|năm|mg|miligam|km/h|giờ|%|triệu|tỷ|mililit|lít)\b",
    re.IGNORECASE,
)


_UNIT_ALIASES = {
    "đồng": "currency",
    "vnđ": "currency",
    "vnd": "currency",
    "triệu": "currency",
    "tỷ": "currency",
    "mg": "mg",
    "miligam": "mg",
    "km/h": "kmh",
    "ngày": "day",
    "tháng": "month",
    "năm": "year",
    "giờ": "hour",
    "%": "percent",
    "mililit": "milliliter",
    "lít": "liter",
}


def _parse_quantity_number(value: str) -> Decimal | None:
    """Parse Vietnamese decimal/thousands separators without losing 0.25."""
    raw = value.replace(" ", "")
    if "," in raw and "." in raw:
        # In Vietnamese notation the last separator is normally decimal.
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        head, tail = raw.rsplit(",", 1)
        raw = raw.replace(",", "") if len(tail) == 3 and head else raw.replace(",", ".")
    elif raw.count(".") == 1:
        head, tail = raw.split(".", 1)
        raw = raw.replace(".", "") if len(tail) == 3 and head else raw
    else:
        raw = raw.replace(".", "")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def _compact_quantity(value: str, unit: str) -> str:
    number = _parse_quantity_number(value)
    if number is None:
        return ""
    normalized_unit = _UNIT_ALIASES.get(_clean_nfc(unit).casefold(), _clean_nfc(unit).casefold())
    if normalized_unit == "currency":
        raw_unit = _clean_nfc(unit).casefold()
        if raw_unit == "triệu":
            number *= Decimal("1000000")
        elif raw_unit == "tỷ":
            number *= Decimal("1000000000")
    normalized_number = format(number.normalize(), "f")
    if "." in normalized_number:
        normalized_number = normalized_number.rstrip("0").rstrip(".")
    normalized_number = normalized_number or "0"
    return normalized_number + normalized_unit


def _extract_quantities(text: str) -> list[str]:
    return [
        compact
        for value, unit in QUANTITATIVE_PATTERN.findall(_clean_nfc(text))
        if (compact := _compact_quantity(value, unit))
    ]


def _unsupported_quantities(answer: str, evidence: list[Any]) -> list[str]:
    evidence_texts: list[str] = []
    for item in evidence:
        if hasattr(item, "document"):
            evidence_texts.append(str(getattr(item.document, "page_content", "")))
        elif isinstance(item, dict):
            evidence_texts.append(str(item.get("text", "")))
    evidence_quantities = set(_extract_quantities(" ".join(evidence_texts)))
    unsupported: list[str] = []
    seen: set[str] = set()
    for quantity in _extract_quantities(answer):
        if quantity in seen:
            continue
        seen.add(quantity)
        if quantity not in evidence_quantities:
            unsupported.append(quantity)
    return unsupported

PUNCT_TO_STRIP = "()[]{}\"'.,;:-\u201c\u201d\u2018\u2019\u00ab\u00bb"


def normalize_so_hieu(so_hieu: str) -> str:
    """Normalizes document identifier string to uppercase trimmed canonical form."""
    cleaned = _clean_nfc(so_hieu).strip().strip(PUNCT_TO_STRIP)
    return cleaned.upper()


def normalize_dieu_number(dieu: Any) -> str | None:
    """Extracts and normalizes article number/code (e.g. 'Điều 113' -> '113', 'Điều 32a' -> '32a', 'Điều 32đ' -> '32đ')."""
    if dieu is None:
        return None
    s = _clean_nfc(dieu).strip()
    match = re.search(r"\b(?:điều)?\s*(\d+[a-zA-ZđĐ]*)\b", s, re.IGNORECASE)
    if match:
        val = match.group(1).lower()
        return val
    return None


def normalize_khoan_number(khoan: Any) -> str | None:
    """Extracts and normalizes clause number (e.g. 'Khoản 1.' -> '1')."""
    if khoan is None:
        return None
    s = _clean_nfc(khoan).strip()
    match = re.search(r"\b(?:khoản)?\s*(\d+)\b", s, re.IGNORECASE)
    if match:
        return match.group(1)
    return None


def extract_so_hieu(text: str) -> list[str]:
    """Extracts unique normalized document identifiers found in text."""
    clean_text = _clean_nfc(text)
    if not clean_text:
        return []
    matches = SO_HIEU_PATTERN.findall(clean_text)
    seen: set[str] = set()
    result: list[str] = []
    for item in matches:
        norm = normalize_so_hieu(item)
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def extract_dieu(text: str) -> list[str]:
    """Extracts unique normalized article identifiers (digits + letters) found in text."""
    clean_text = _clean_nfc(text)
    if not clean_text:
        return []
    matches = DIEU_PATTERN.findall(clean_text)
    seen: set[str] = set()
    result: list[str] = []
    for item in matches:
        norm = item.strip().lower()
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def extract_khoan(text: str) -> list[str]:
    """Extracts unique clause numbers found in text."""
    clean_text = _clean_nfc(text)
    if not clean_text:
        return []
    matches = KHOAN_PATTERN.findall(clean_text)
    seen: set[str] = set()
    result: list[str] = []
    for item in matches:
        norm = item.strip()
        if norm and norm not in seen:
            seen.add(norm)
            result.append(norm)
    return result


def extract_metadata_from_evidence_item(item: Any) -> dict[str, Any]:
    """Extracts standard metadata dictionary from various evidence structures.

    Supports HybridResult, LangChain Document, compact dicts with metadata/citation,
    and plain metadata dicts.
    """
    if hasattr(item, "document") and hasattr(item.document, "metadata"):
        return dict(item.document.metadata)
    if hasattr(item, "metadata") and isinstance(item.metadata, dict):
        return dict(item.metadata)
    if isinstance(item, dict):
        if "metadata" in item and isinstance(item["metadata"], dict):
            meta = dict(item["metadata"])
            if "id" not in meta and "document_id" in item:
                meta["id"] = item["document_id"]
            return meta
        if "citation" in item and isinstance(item["citation"], dict):
            meta = dict(item["citation"])
            if "id" not in meta and "document_id" in item:
                meta["id"] = item["document_id"]
            return meta
        return dict(item)
    return {}


def citation_from_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Converts a metadata dictionary into a standardized citation record."""
    return {
        "document_id": metadata.get("id") or metadata.get("document_id"),
        "so_hieu": metadata.get("so_hieu"),
        "ten_van_ban": metadata.get("ten_van_ban"),
        "chuong": metadata.get("chuong"),
        "dieu": metadata.get("dieu"),
        "khoan": metadata.get("khoan"),
        "source": metadata.get("source"),
        "status": metadata.get("status", "unknown"),
        "effective_from": metadata.get("effective_from") or None,
    }


@dataclass
class GroundingIndex:
    """Index of verified legal grounding elements extracted from retrieved evidence."""
    valid_so_hieu: set[str] = field(default_factory=set)
    valid_dieu: set[str] = field(default_factory=set)
    valid_khoan: set[str] = field(default_factory=set)
    valid_dieu_by_so_hieu: dict[str, set[str]] = field(default_factory=dict)
    doc_ids: set[str] = field(default_factory=set)
    evidence_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    evidence_items: list[dict[str, Any]] = field(default_factory=list)


def build_grounding_index(evidence: list[Any]) -> GroundingIndex:
    """Builds a Grounding Index from a list of evidence items."""
    index = GroundingIndex()
    for item in evidence:
        meta = extract_metadata_from_evidence_item(item)
        if not meta:
            continue
        index.evidence_items.append(meta)
        doc_id = str(meta.get("id") or meta.get("document_id") or "")
        if doc_id:
            index.doc_ids.add(doc_id)
            index.evidence_by_id[doc_id] = meta

        # Extract and normalize so_hieu from metadata fields
        primary_sh: list[str] = []
        raw_sh = meta.get("so_hieu")
        if raw_sh:
            extracted_from_field = extract_so_hieu(str(raw_sh))
            if extracted_from_field:
                primary_sh.extend(extracted_from_field)
            else:
                norm_sh = normalize_so_hieu(str(raw_sh))
                if norm_sh:
                    primary_sh.append(norm_sh)

        title_sh: list[str] = []
        raw_title = meta.get("ten_van_ban")
        if raw_title:
            title_sh.extend(extract_so_hieu(str(raw_title)))

        # All candidates are recognized as valid so_hieu in evidence
        for sh in (*primary_sh, *title_sh):
            if sh:
                index.valid_so_hieu.add(sh)

        # Articles belong to primary_sh (or title_sh if primary_sh is missing)
        article_so_hieu = primary_sh if primary_sh else title_sh
        raw_dieu = meta.get("dieu") or meta.get("tieu_de_dieu") or meta.get("title")
        dieu_norm = normalize_dieu_number(raw_dieu)
        if dieu_norm:
            index.valid_dieu.add(dieu_norm)
            for sh in article_so_hieu:
                if sh:
                    index.valid_dieu_by_so_hieu.setdefault(sh, set()).add(dieu_norm)

        # Extract and normalize khoan
        raw_khoan = meta.get("khoan")
        khoan_norm = normalize_khoan_number(raw_khoan)
        if khoan_norm:
            index.valid_khoan.add(khoan_norm)

    return index


@dataclass
class CitationGuardrailResult:
    """Result of citation verification guardrail check."""
    status: str
    verified_answer: str
    citations: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)

    def __iter__(self):
        """Allows unpacking as (status, verified_answer, citations, warnings)."""
        return iter((self.status, self.verified_answer, self.citations, self.warnings))

    @property
    def is_verified(self) -> bool:
        return self.status == "verified"


def _check_article_law_cross_reference(
    answer: str,
    valid_dieu_by_so_hieu: dict[str, set[str]],
) -> list[str]:
    """Checks whether an article cited in conjunction with a document number actually belongs to it."""
    if not valid_dieu_by_so_hieu:
        return []
    clean_answer = _clean_nfc(answer)
    mismatches: list[str] = []
    dieu_matches = list(DIEU_PATTERN.finditer(clean_answer))
    so_hieu_matches = list(SO_HIEU_PATTERN.finditer(clean_answer))

    for d_match in dieu_matches:
        d_val = d_match.group(1).lower()
        d_start = d_match.start()
        d_end = d_match.end()

        nearest_sh = None
        min_dist = float("inf")

        for sh_match in so_hieu_matches:
            sh_val = normalize_so_hieu(sh_match.group(1))
            sh_start = sh_match.start()
            sh_end = sh_match.end()

            dist = abs(d_start - sh_start)
            if dist >= 90 or dist >= min_dist:
                continue

            # Extract the connecting span between article and document number
            if d_start < sh_start:
                span = clean_answer[d_end:sh_start]
                # If article has title separator dot (e.g. "Điều 113. Nghỉ hằng năm của..."),
                # strip the leading dot so it is not treated as a sentence boundary.
                if span.startswith("."):
                    span = span[1:]
            else:
                span = clean_answer[sh_end:d_start]

            # A valid cross-reference citation must be within the same clause/sentence.
            # Paragraph breaks (\n, \r), sentence breaks (. followed by capital/digit),
            # or clause separators (; followed by space) indicate separate statements.
            if "\n" in span or "\r" in span:
                continue
            if re.search(r"[\.!?]\s+[A-ZÀ-Ỹ0-9]", span):
                continue
            if re.search(r";\s+", span):
                continue

            min_dist = dist
            nearest_sh = sh_val

        if nearest_sh and nearest_sh in valid_dieu_by_so_hieu:
            allowed_articles = valid_dieu_by_so_hieu[nearest_sh]
            if d_val not in allowed_articles:
                msg = f"Điều {d_val} không thuộc văn bản {nearest_sh}"
                if msg not in mismatches:
                    mismatches.append(msg)
    return mismatches


def verify_citations_guardrail(
    answer: str,
    evidence: list[Any],
    cited_document_ids: list[str] | None = None,
    require_cited_ids: bool = False,
    status_on_hallucination: str = "unverified",
    verify_quantitative_claims: bool = False,
) -> CitationGuardrailResult:
    """Verifies citations in answer against evidence Grounding Index.

    Args:
        answer: The text generated by LLM / domain agent / synthesizer.
        evidence: The retrieved evidence list (HybridResult, Document, dicts).
        cited_document_ids: Explicit document IDs cited by caller, if any.
        require_cited_ids: If True and cited_document_ids is empty, treat as insufficient.
        status_on_hallucination: Status to set when hallucination is detected (default 'unverified').

    Returns:
        CitationGuardrailResult with status, verified_answer, citations, and warnings.
    """
    clean_ans = _clean_nfc(answer)

    # 0. Check for empty or whitespace answer
    if not clean_ans or not clean_ans.strip():
        return CitationGuardrailResult(
            status="insufficient_evidence",
            verified_answer=INSUFFICIENT_EVIDENCE,
            citations=[],
            warnings=["Câu trả lời rỗng hoặc không có nội dung."],
        )

    # 1. Check for standard insufficient evidence phrase
    if contains_insufficient_evidence(clean_ans):
        return CitationGuardrailResult(
            status="insufficient_evidence",
            verified_answer=clean_ans,
            citations=[],
            warnings=[],
        )

    # 2. Check for empty evidence pool
    if not evidence:
        return CitationGuardrailResult(
            status="insufficient_evidence",
            verified_answer=INSUFFICIENT_EVIDENCE,
            citations=[],
            warnings=["Không có tài liệu chứng cứ (evidence) nào được cung cấp."],
        )

    # 3. Build Grounding Index from evidence metadata
    index = build_grounding_index(evidence)

    # 3a. Quantitative claims must appear in retrieved text, not only metadata.
    unsupported_quantities = (
        _unsupported_quantities(clean_ans, evidence)
        if verify_quantitative_claims
        else []
    )
    if unsupported_quantities:
        warning_msg = (
            "Unsupported quantitative claim not found in evidence: "
            + ", ".join(unsupported_quantities)
        )
        logger.warning("Citation guardrail unsupported quantitative claim: %s", warning_msg)
        return CitationGuardrailResult(
            status=status_on_hallucination,
            verified_answer=f"{clean_ans}\n\n[{warning_msg}]",
            citations=[],
            warnings=[warning_msg],
        )
    # 4. Check explicit cited_document_ids if required or supplied
    if require_cited_ids and (not cited_document_ids):
        return CitationGuardrailResult(
            status="insufficient_evidence",
            verified_answer=INSUFFICIENT_EVIDENCE,
            citations=[],
            warnings=["Không có tài liệu chứng cứ nào được viện dẫn."],
        )

    if cited_document_ids is not None and len(cited_document_ids) > 0:
        invalid_doc_ids = [did for did in cited_document_ids if did not in index.doc_ids]
        if invalid_doc_ids:
            warning_msg = (
                f"CẢNH BÁO: Tài liệu trích dẫn không tồn tại trong kết quả truy xuất (ID: {', '.join(invalid_doc_ids)})."
            )
            return CitationGuardrailResult(
                status="insufficient_evidence",
                verified_answer=INSUFFICIENT_EVIDENCE,
                citations=[],
                warnings=[warning_msg],
            )

    # 5. Extract citations from the answer text
    extracted_so_hieu = extract_so_hieu(clean_ans)
    extracted_dieu = extract_dieu(clean_ans)

    # 6. Detect hallucinations against Grounding Index
    hallucinated_so_hieu = [sh for sh in extracted_so_hieu if sh not in index.valid_so_hieu]
    hallucinated_dieu = [d for d in extracted_dieu if d not in index.valid_dieu]
    mismatches = _check_article_law_cross_reference(clean_ans, index.valid_dieu_by_so_hieu)

    has_hallucination = bool(hallucinated_so_hieu or hallucinated_dieu or mismatches)

    if has_hallucination:
        parts: list[str] = []
        if hallucinated_dieu:
            parts.append(f"Điều {', '.join(hallucinated_dieu)}")
        if hallucinated_so_hieu:
            parts.append(f"Số hiệu {', '.join(hallucinated_so_hieu)}")
        if mismatches:
            parts.extend(mismatches)
        details = " / ".join(parts)
        warning_msg = (
            f"CẢNH BÁO: Phát hiện trích dẫn pháp lý không có căn cứ trong tài liệu truy xuất ({details}). "
            f"Trạng thái hạ xuống {status_on_hallucination}."
        )
        logger.warning("Citation guardrail hallucination detected: %s", warning_msg)
        verified_answer = f"{clean_ans}\n\n[{warning_msg}]"
        return CitationGuardrailResult(
            status=status_on_hallucination,
            verified_answer=verified_answer,
            citations=[],
            warnings=[warning_msg],
        )

    # 7. Citations are grounded and valid
    # Resolve citations list
    if cited_document_ids is not None and len(cited_document_ids) > 0:
        citations = [
            citation_from_metadata(index.evidence_by_id[did])
            for did in cited_document_ids
            if did in index.evidence_by_id
        ]
    else:
        # Match evidence items by extracted dieu or so_hieu
        matched: list[dict[str, Any]] = []
        if extracted_dieu or extracted_so_hieu:
            for meta in index.evidence_items:
                m_sh = normalize_so_hieu(str(meta.get("so_hieu") or ""))
                m_d = normalize_dieu_number(meta.get("dieu"))
                if (m_sh and m_sh in extracted_so_hieu) or (m_d and m_d in extracted_dieu):
                    matched.append(citation_from_metadata(meta))
        if not matched:
            matched = [citation_from_metadata(meta) for meta in index.evidence_items]

        # Deduplicate citations by document_id
        seen_ids: set[str] = set()
        citations = []
        for c in matched:
            cid = str(c.get("document_id") or repr(c))
            if cid not in seen_ids:
                seen_ids.add(cid)
                citations.append(c)

    return CitationGuardrailResult(
        status="verified",
        verified_answer=answer,
        citations=citations,
        warnings=[],
    )


# Interface Contract alias
def verify_answer_citations(
    answer: str,
    evidence: list[Any],
    cited_document_ids: list[str] | None = None,
) -> tuple[str, str, list[dict[str, Any]], list[str]]:
    """Contract specified in SCOPE.md / PROJECT.md:
    (status, verified_answer, citations, warnings)
    """
    res = verify_citations_guardrail(answer, evidence, cited_document_ids=cited_document_ids)
    return res.status, res.verified_answer, res.citations, res.warnings
