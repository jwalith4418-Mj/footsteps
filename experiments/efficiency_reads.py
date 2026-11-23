"""Count same-argument reads and shortened receipts without exporting their contents."""

import argparse
import json
from collections import Counter
from pathlib import Path

from experiments.game_efficiency import READ_TOOLS


def counts(trace):
    counts = Counter()
    preceding = None
    preceding_idle_cursor = None
    for line in trace.read_text().splitlines():
        row = json.loads(line)
        result = row["result"]
        notice = row.get("opportunity", {})
        idle_cursor = None
        if (
            row["tool"] == "get_state"
            and "cursor" in result
            and notice.get("owe_action") is False
            and notice.get("can_speak") is False
        ):
            idle_cursor = result["cursor"]
            counts["idle_state_reads"] += 1
            counts["consecutive_same_idle_cursor"] += idle_cursor == preceding_idle_cursor
        preceding_idle_cursor = idle_cursor
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
