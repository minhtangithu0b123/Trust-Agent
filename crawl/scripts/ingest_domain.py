import argparse
import logging

from app.config import get_settings
from app.domains import DOMAIN_CONFIGS
from app.vectorstore import ingest_domain


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest one configured legal domain")
    parser.add_argument("domain", choices=sorted(DOMAIN_CONFIGS))
    parser.add_argument("--prune-stale", action="store_true", help="Remove Chroma chunks no longer present in the JSON corpus")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    result = ingest_domain(get_settings(), args.domain, prune_stale=args.prune_stale)
    print({"domain": args.domain, **result.__dict__})
