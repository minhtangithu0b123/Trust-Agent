"""Create a deterministic Merkle-root manifest for receipts awaiting anchoring."""

import json
from pathlib import Path

from app.provenance import prepare_batch


if __name__ == "__main__":
    batch = prepare_batch()
    if batch is None:
        print("No receipts are waiting for a batch.")
    else:
        output = Path("reports") / f"provenance-{batch['root'][:16]}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(batch, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Prepared {batch['count']} receipts: {batch['root']}")
        print(f"Manifest: {output}")
