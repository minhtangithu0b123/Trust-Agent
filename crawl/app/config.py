from dataclasses import replace
from functools import lru_cache
from pathlib import Path

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
    api_host: str = "127.0.0.1"
    api_port: int = 8000
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"

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