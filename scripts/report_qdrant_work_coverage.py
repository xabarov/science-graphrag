#!/usr/bin/env python3
"""Report distinct work_id values in Qdrant ``chunks`` collection (Wave 5 corpus acceptance)."""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from qdrant_client import QdrantClient

from science_graphrag.config import get_settings


def main() -> int:
    """CLI entry: print distinct Qdrant ``work_id`` counts (optional min threshold)."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-works",
        type=int,
        default=0,
        help="Exit 1 if distinct work_id count is below this threshold (e.g. 16).",
    )
    args = parser.parse_args()

    s = get_settings()
    client = QdrantClient(url=s.qdrant_url, check_compatibility=False)
    collection = s.qdrant_collection

    cols = {c.name for c in client.get_collections().collections}
    if collection not in cols:
        print(f"Collection {collection!r} missing; distinct_work_ids=0", flush=True)
        return 1 if args.min_works > 0 else 0

    work_ids: Counter[str] = Counter()
    offset = None
    while True:
        points, offset = client.scroll(
            collection_name=collection,
            limit=256,
            with_payload=True,
            with_vectors=False,
            offset=offset,
        )
        for p in points:
            wid = (p.payload or {}).get("work_id")
            if isinstance(wid, str) and wid.strip():
                work_ids[wid.strip()] += 1
        if offset is None:
            break

    n = len(work_ids)
    print(f"qdrant_url={s.qdrant_url} collection={collection}", flush=True)
    print(f"distinct_work_ids={n} total_points_with_work_id={sum(work_ids.values())}", flush=True)
    for wid, cnt in work_ids.most_common():
        print(f"  {wid}\tpoints={cnt}", flush=True)

    if args.min_works > 0 and n < args.min_works:
        print(
            f"FAIL: distinct_work_ids={n} < --min-works={args.min_works}",
            file=sys.stderr,
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
