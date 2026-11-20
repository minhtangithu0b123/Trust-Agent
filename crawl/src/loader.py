"""Backward-compatible entry point for the legal crawler.

The canonical implementation lives in ``app.crawler`` so crawler output and
the FastAPI ingest pipeline share one schema. New code should import from
``app.crawler`` directly.
"""

from __future__ import annotations

from pathlib import Path

from app.crawler import CrawlSource, LegalCrawler, extract_so_hieu, html_to_text, legal_records


class DocumentLoader:
    """Compatibility wrapper returning canonical corpus records."""

    def __init__(self, raw_dir: str):
        self.raw_dir = Path(raw_dir)
        self.crawler = LegalCrawler()

    def load_documents(self) -> list[dict]:
        sources: list[CrawlSource] = []
        for path in sorted(self.raw_dir.iterdir() if self.raw_dir.exists() else []):
            if path.suffix.lower() in {".html", ".htm", ".pdf", ".txt", ".md"}:
                sources.append(CrawlSource(str(path), title=path.stem))
        return self.crawler.crawl_sources(sources)


__all__ = ["CrawlSource", "DocumentLoader", "LegalCrawler", "extract_so_hieu", "html_to_text", "legal_records"]
