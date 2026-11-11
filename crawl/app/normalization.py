import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from ftfy import fix_text
from langchain_core.documents import Document

from .domains import DomainConfig, metadata_with_defaults

REQUIRED_FIELDS = (
    "source", "so_hieu", "ten_van_ban", "chuong",
    "dieu", "tieu_de_dieu", "khoan", "text",
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
    return text.replace("Lu\u00e2t", "Lu\u1eadt")


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

    values = {field: repair_text(record.get(field)) for field in REQUIRED_FIELDS}
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
        "khoan": values["khoan"],
        "source": values["source"],
        "effective_from": repair_text(record.get("effective_from")) or defaults.get("effective_from", ""),
        "status": repair_text(record.get("status")) or defaults.get("status", "unknown"),
    }
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
    return [
        normalize_record(record, index, domain=domain_config.name, metadata_defaults=defaults)
        for index, record in enumerate(load_records(path))
    ]


def load_labor_documents(path: Path, domain: str = "labor") -> list[tuple[str, Document]]:
    # Backward-compatible helper retained for existing Labor callers/tests.
    from .domains import get_domain_config
    return load_documents(path, get_domain_config(domain))