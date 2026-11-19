"""Create an ingestible JSON corpus from local legal files or urls.json."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.crawler import CrawlSource, LegalCrawler, write_corpus
from app.domains import get_domain_config


def main() -> None:
    parser = argparse.ArgumentParser(description="Crawl legal sources into Trust-Agent JSON schema")
    parser.add_argument("domain", choices=("traffic", "labor", "accounting", "tax"))
    parser.add_argument("--input", action="append", help="Local HTML/PDF/TXT/MD file; repeatable")
    parser.add_argument("--input-dir", type=Path, help="Directory of local HTML/PDF/TXT/MD files")
    parser.add_argument("--urls", type=Path, help="JSON list of {url,title} objects")
    parser.add_argument("--output", type=Path, help="Output JSON path; defaults to configured domain corpus")
    args = parser.parse_args()

    config = get_domain_config(args.domain)
    sources: list[CrawlSource] = []
    for filename in args.input or []:
        sources.append(CrawlSource(filename, title=Path(filename).stem))
    if args.input_dir:
        for path in sorted(args.input_dir.iterdir()):
            if path.suffix.lower() in {".html", ".htm", ".pdf", ".txt", ".md"}:
                sources.append(CrawlSource(str(path), title=path.stem))
    if args.urls:
        payload = json.loads(args.urls.read_text(encoding="utf-8"))
        sources.extend(CrawlSource(item["url"], item.get("title", "")) for item in payload if item.get("url"))
    if not sources:
        raise SystemExit("Provide --input or --urls. Existing JSON corpora are already ingest-ready and are not recrawled.")

    output = args.output or Path(config.data_path)
    if not output.is_absolute():
        output = Path(__file__).resolve().parents[1] / output
    new_records = LegalCrawler().crawl_sources(sources)
    existing: list[dict] = []
    if output.exists():
        try:
            payload = json.loads(output.read_text(encoding="utf-8"))
            existing = payload if isinstance(payload, list) else []
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Existing output is not valid JSON; refusing to overwrite: {output}") from exc
    count = write_corpus([*existing, *new_records], output)
    print({"domain": config.name, "output": str(output), "records": count})


if __name__ == "__main__":
    main()
