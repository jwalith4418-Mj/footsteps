"""Count same-argument reads and shortened receipts without exporting their contents."""

import argparse
import json
from collections import Counter
from pathlib import Path

from experiments.game_efficiency import READ_TOOLS


def counts(trace):
    counts = Counter()
    preceding = None
    for line in trace.read_text().splitlines():
        row = json.loads(line)
        result = row["result"]
        if row["tool"] not in READ_TOOLS or "error" in result:
            preceding = None
            continue
        # Same referee revision can include new remarks. Only the session can attest
        # that the entire seat cursor was unchanged when it issued a shortened receipt.
        query = (row["revision"], row["tool"], row["arguments"])
        counts["reads"] += 1
        counts["consecutive_same_args_revision"] += query == preceding
        counts["shortened"] += "repeat" in result
        preceding = query
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("private", type=Path)
    args = parser.parse_args()
    files = sorted(args.private.glob("seat-*.jsonl"))
    if not files:
        parser.error("expected a directory containing private seat traces")
    print(json.dumps({f.stem: counts(f) for f in files}, indent=2))
