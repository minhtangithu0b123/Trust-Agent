from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class DomainConfig:
    name: str
    collection_name: str
    data_path: str
    prompt_name: str
    metadata_defaults: dict[str, str]


DOMAIN_CONFIGS: dict[str, DomainConfig] = {
    "labor": DomainConfig(
        name="labor",
        collection_name="legal_labor",
        data_path="data/raw/lao_dong.json",
        prompt_name="legal_labor_agent",
        metadata_defaults={"status": "unknown", "effective_from": ""},
    ),
    # The current accounting corpus is tax-law data in thue.json; keep this
    # mapping configurable so it can be replaced by a dedicated accounting corpus.
    "accounting": DomainConfig(
        name="accounting",
        collection_name="legal_accounting",
        data_path="data/raw/thue.json",
        prompt_name="legal_accounting_agent",
        metadata_defaults={"status": "unknown", "effective_from": ""},
    ),
    "traffic": DomainConfig(
        name="traffic",
        collection_name="legal_traffic",
        data_path="data/raw/giao thông.json",
        prompt_name="legal_traffic_agent",
        metadata_defaults={"status": "unknown", "effective_from": ""},
    ),
}


class UnknownDomainError(ValueError):
    pass


class CorpusNotFoundError(FileNotFoundError):
    pass


def get_domain_config(domain: str) -> DomainConfig:
    key = domain.strip().lower()
    try:
        return DOMAIN_CONFIGS[key]
    except KeyError as exc:
        raise UnknownDomainError(
            f"Unsupported domain '{domain}'. Available domains: {', '.join(sorted(DOMAIN_CONFIGS))}"
        ) from exc


def resolve_data_path(config: DomainConfig, root_dir: Path) -> Path:
    path = Path(config.data_path)
    return path if path.is_absolute() else root_dir / path


def metadata_with_defaults(config: DomainConfig, values: dict[str, Any]) -> dict[str, Any]:
    result = dict(config.metadata_defaults)
    result.update(values)
    return result