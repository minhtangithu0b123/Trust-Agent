import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from ftfy import fix_text
from langchain_core.documents import Document

from .domains import DomainConfig, metadata_with_defaults

REQUIRED_FIELDS = (
    "source", "so_hieu", "ten_van_ban", "chuong",
    "dieu", "tieu_de_dieu", "khoan", "text",
)

# Some crawled PDFs expose only an internal filename (for example ``thue1``)
# as ``ten_van_ban``. Use the legal identifier as the source of truth for
# citations so the model receives the actual law name.
CANONICAL_DOCUMENT_TITLES = {
    "108/2025/QH15": "Luật Quản lý thuế",
}

KNOWN_OCR_REPAIRS = {
    "địch vụ": "dịch vụ",
    "chỉ nhận thông tin": "ghi nhận thông tin",
    "gềm": "gồm",
    "gềm hóa đơn": "gồm hóa đơn",
    "kết nói dữ liệu": "kết nối dữ liệu",
    "kết nói đữ liệu": "kết nối dữ liệu",
    "đữ liệu": "dữ liệu",
    "muà hàng": "mua hàng",
    "hóa 34 đơn": "hóa đơn",
}


def _label_number(value: str, label: str) -> str:
    match = re.search(rf"{label}\s+(\d+[A-Za-z]?)", value, re.IGNORECASE)
    return match.group(1) if match else ""


def _document_type(so_hieu: str, title: str) -> str:
    value = f"{so_hieu} {title}".casefold()
    if "nđ-cp" in value or "nghị định" in value:
        return "decree"
    if "/qh" in value or "luật" in value:
        return "law"
    if "thông tư" in value or "/tt-" in value:
        return "circular"
    return "other"


def _topic_tags(domain: str, text: str) -> str:
    value = text.casefold()
    groups = {
        "traffic": {
            "alcohol": ("nồng độ cồn", "rượu bia"),
            "helmet": ("mũ bảo hiểm", "cài quai"),
            "red_light": ("đèn tín hiệu", "đèn đỏ"),
            "speed": ("tốc độ", "giới hạn tốc độ"),
        },
        "labor": {
            "trial": ("thử việc",),
            "leave": ("nghỉ hằng năm", "nghỉ phép"),
            "wage": ("tiền lương", "tiền công"),
            "contract": ("hợp đồng lao động",),
        },
        "accounting": {
            "vat": ("giá trị gia tăng", "gtgt", "vat"),
            "personal_income_tax": ("thuế thu nhập cá nhân", "tncn"),
            "invoice": ("hóa đơn điện tử", "hóa đơn"),
            "accounting": ("nguyên tắc kế toán", "chứng từ kế toán", "sổ kế toán"),
        },
    }
    return "|".join(
        tag for tag, signals in groups.get(domain, {}).items()
        if any(signal in value for signal in signals)
    )


def repair_text(value: Any) -> str:
    """Normalize text and repair common UTF-8-as-Latin-1 mojibake."""
    if value is None:
        return ""
    text = str(value).replace("\x00", "").strip()
    for _ in range(3):
        fixed = fix_text(text)
        if fixed == text:
            break
        text = fixed
    text = text.replace("Lu\u00e2t", "Lu\u1eadt")
    for broken, repaired in KNOWN_OCR_REPAIRS.items():
        text = text.replace(broken, repaired)
    return text


def _repair_domain_fields(values: dict[str, str], domain: str) -> dict[str, str]:
    """Repair small, deterministic extraction errors without rewriting raw data.

    Some crawled accounting records split the Article 6 title between
    ``tieu_de_dieu`` (``Nguyên``) and ``text`` (``tắc kế toán``).  Keeping the
    phrase together in the normalized document makes BM25 and dense retrieval
    see the legal topic while preserving the original raw corpus.
    """
    repaired = dict(values)
    if (
        domain == "accounting"
        and repaired["so_hieu"] == "88/2015/QH13"
        and repaired["dieu"] == "Điều 6"
    ):
        title = repaired["tieu_de_dieu"].strip()
        text = repaired["text"].strip()
        if title == "Nguyên" or "tắc kế toán" in text.casefold():
            repaired["tieu_de_dieu"] = "Nguyên tắc kế toán"
            if "nguyên tắc kế toán" not in text.casefold():
                repaired["text"] = f"Nguyên tắc kế toán. {text}"
    return repaired


def load_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if isinstance(payload, dict):
        payload = payload.get("legal_documents", payload.get("documents", []))
    if not isinstance(payload, list):
        raise ValueError(f"JSON corpus must contain a list of records: {path}")
    return payload


def normalize_record(
    record: dict[str, Any],
    index: int,
    domain: str = "labor",
    metadata_defaults: Mapping[str, Any] | None = None,
) -> tuple[str, Document]:
    missing = [field for field in REQUIRED_FIELDS if field not in record]
    if missing:
        raise ValueError(f"Record {index} is missing fields: {missing}")

    values = _repair_domain_fields(
        {field: repair_text(record.get(field)) for field in REQUIRED_FIELDS},
        domain,
    )
    canonical_title = CANONICAL_DOCUMENT_TITLES.get(values["so_hieu"])
    if canonical_title:
        values["ten_van_ban"] = canonical_title
    if not values["text"]:
        raise ValueError(f"Record {index} has empty text")
    fingerprint = "|".join([
        domain, values["source"], values["so_hieu"], values["dieu"],
        values["khoan"], values["text"], str(index),
    ])
    record_id = str(record.get("id") or record.get("document_id") or "")
    if not record_id:
        record_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:24]
    defaults = dict(metadata_defaults or {})
    base_metadata = {
        "id": record_id,
        "domain": domain,
        "so_hieu": values["so_hieu"],
        "ten_van_ban": values["ten_van_ban"],
        "chuong": values["chuong"],
        "dieu": values["dieu"],
        "tieu_de_dieu": values["tieu_de_dieu"],
        "khoan": values["khoan"],
        "source": values["source"],
        "effective_from": repair_text(record.get("effective_from")) or defaults.get("effective_from", ""),
        "status": repair_text(record.get("status")) or defaults.get("status", "unknown"),
    }
    article_number = _label_number(values["dieu"], "Điều")
    clause_number = _label_number(values["khoan"], "Khoản")
    base_metadata.update({
        "article_number": article_number,
        "clause_number": clause_number,
        "structure_key": f"{values['so_hieu']}:{values['dieu']}:{values['khoan']}",
        "document_type": _document_type(values["so_hieu"], values["ten_van_ban"]),
        "topic_tags": _topic_tags(domain, f"{values['tieu_de_dieu']} {values['text']}"),
    })
    if domain == "traffic":
        base_metadata["vehicle_class"] = {
            "6": "car",
            "7": "motorbike",
            "8": "specialized_vehicle",
            "9": "bicycle",
        }.get(article_number, "")
    for k, v in record.items():
        if k not in base_metadata and k not in REQUIRED_FIELDS:
            if isinstance(v, (str, int, float, bool)):
                base_metadata[k] = v
            elif isinstance(v, (list, dict)):
                base_metadata[k] = json.dumps(v, ensure_ascii=False)
    metadata = dict(metadata_defaults or {})
    metadata.update(base_metadata)
    return record_id, Document(page_content=values["text"], metadata=metadata)


def load_documents(path: Path, domain_config: DomainConfig) -> list[tuple[str, Document]]:
    defaults = metadata_with_defaults(domain_config, {})
    normalized = [
        normalize_record(record, index, domain=domain_config.name, metadata_defaults=defaults)
        for index, record in enumerate(load_records(path))
    ]
    # A few crawlers emit the same legal clause twice: once with a scraped
    # header ("[...]- Nguồn: ...- Nội dung:") and once as clean clause text.
    # Keep one best record per exact legal structure so retrieval does not
    # waste candidates on duplicates. Different laws/versions remain distinct
    # because the structure key includes the document number.
    selected: dict[str, tuple[str, Document]] = {}
    for record_id, document in normalized:
        key = str(document.metadata.get("structure_key", record_id))
        current = selected.get(key)
        if current is None or _document_quality(document) > _document_quality(current[1]):
            selected[key] = (record_id, document)
    return list(selected.values())


def _document_quality(document: Document) -> tuple[int, int, int, str]:
    """Rank duplicate records so clean legal text wins over scraped wrappers."""
    text = document.page_content.strip()
    prefix = text[:600].casefold()
    wrapper_penalty = int(text.startswith("[") and ("nguồn:" in prefix or "nội dung:" in prefix))
    corruption_penalty = int("�" in text) + int("?" in text[:300])
    return (
        1 - wrapper_penalty,
        1 - corruption_penalty,
        len(text),
        str(document.metadata.get("source", "")),
    )


def load_labor_documents(path: Path, domain: str = "labor") -> list[tuple[str, Document]]:
    # Backward-compatible helper retained for existing Labor callers/tests.
    from .domains import get_domain_config
    return load_documents(path, get_domain_config(domain))
