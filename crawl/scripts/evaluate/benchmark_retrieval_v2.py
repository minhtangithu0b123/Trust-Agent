"""Offline retrieval benchmark for benchmark_v2.jsonl.

Usage from crawl/: python scripts/evaluate/benchmark_retrieval_v2.py --k 5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

CRAWL_DIR = Path(__file__).resolve().parents[2]
if str(CRAWL_DIR) not in sys.path:
    sys.path.insert(0, str(CRAWL_DIR))

from app.config import get_settings  # noqa: E402
from app.retrieval import get_hybrid_retriever  # noqa: E402


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def hit(results, keywords: list[str]) -> bool:
    terms = [term.casefold() for term in keywords]
    return any(all(term in result.document.page_content.casefold() for term in terms) for result in results)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--cases", type=Path, default=Path(__file__).with_name("benchmark_v2.jsonl"))
    args = parser.parse_args()
    settings = get_settings()
    cases = load_cases(args.cases)
    buckets: dict[str, list[bool]] = {}
    corpus_buckets: dict[str, list[bool]] = {}
    reciprocal_ranks: list[float] = []

    for case in cases:
        retriever = get_hybrid_retriever(settings, domain=case["domain"])
        results = retriever.search(case["query"], k=args.k)
        keywords = case["expected_keywords"]
        corpus_buckets.setdefault(case["domain"], []).append(
            any(
                all(term.casefold() in document.page_content.casefold() for term in keywords)
                for document in retriever._documents.values()
            )
        )
        ranks = []
        for rank, result in enumerate(results, 1):
            text = result.document.page_content.casefold()
            if all(term.casefold() in text for term in keywords):
                ranks.append(rank)
        reciprocal_ranks.append(1 / ranks[0] if ranks else 0.0)
        buckets.setdefault(case["domain"], []).append(bool(ranks))

    total = len(cases)
    print(f"cases={total} k={args.k}")
    for domain, values in buckets.items():
        print(f"{domain}: recall@{args.k}={sum(values) / len(values):.4f} ({sum(values)}/{len(values)})")
        coverage = corpus_buckets[domain]
        print(f"{domain}: corpus_coverage={sum(coverage) / len(coverage):.4f} ({sum(coverage)}/{len(coverage)})")
    print(f"MRR@{args.k}={sum(reciprocal_ranks) / total:.4f}")


if __name__ == "__main__":
    main()
