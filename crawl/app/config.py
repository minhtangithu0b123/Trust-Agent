from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from .domains import DomainConfig, get_domain_config

ROOT_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    labor_data_path: str = "data/raw/lao_dong.json"
    chroma_persist_dir: str = "data/chroma"
    chroma_collection: str = "legal_labor"
    labor_domain: str = "labor"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    embedding_device: str = "cpu"
    reranker_enabled: bool = False
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_candidate_k: int = 20
    reranker_batch_size: int = 8
    reranker_max_length: int = 256
    reflection_enabled: bool = True
    reflection_max_rounds: int = 1
    self_rag_enabled: bool = True
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    llm_provider: str = "gemini"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.5-flash-lite"
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        validation_alias=AliasChoices("OPENAI_MODEL_NAME", "OPENAI_MODEL", "openai_model"),
    )
    x402_enabled: bool = False
    x402_price_usd: str = "0.01"
    x402_network: str = "eip155:43113"
    x402_asset_address: str = ""
    x402_asset_decimals: int = 6
    x402_asset_name: str = "USD Coin"
    x402_asset_version: str = "2"
    x402_pay_to: str = ""
    x402_facilitator_url: str = ""
    index_version: str = "development"
    provenance_db_path: str = "data/provenance.sqlite3"
    database_url: str = Field(
        default="sqlite:///./data/conversations.db",
        validation_alias=AliasChoices("DATABASE_URL", "database_url"),
    )
    reward_admin_token: str = ""
    ingest_admin_token: str = ""
    api_access_token: str = ""
    require_api_key: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    def resolve_path(self, value: str) -> Path:
        path = Path(value)
        return path if path.is_absolute() else ROOT_DIR / path

    @property
    def labor_path(self) -> Path:
        return self.resolve_path(self.labor_data_path)

    @property
    def chroma_path(self) -> Path:
        return self.resolve_path(self.chroma_persist_dir)

    @property
    def provenance_path(self) -> Path:
        return self.resolve_path(self.provenance_db_path)

    @property
    def db_url(self) -> str:
        return self.database_url

    def domain_config(self, domain: str) -> DomainConfig:
        config = get_domain_config(domain)
        # Preserve the existing Labor environment variables as an override.
        if config.name == self.labor_domain:
            return replace(
                config,
                data_path=self.labor_data_path,
                collection_name=self.chroma_collection,
            )
        return config


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
