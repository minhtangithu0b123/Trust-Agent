"""Ensure all configured corpora exist before starting the API."""

import logging

from app.config import get_settings
from app.vectorstore import ingest_domain


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    for domain in ("traffic", "labor", "accounting"):
        result = ingest_domain(settings, domain)
        logging.info(
            "Corpus ready: domain=%s count=%s added=%s skipped=%s",
            domain,
            result.collection_count,
            result.added,
            result.skipped_existing,
        )


if __name__ == "__main__":
    main()
