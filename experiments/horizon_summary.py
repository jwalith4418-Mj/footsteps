"""Score four-seat horizon probes from recorded public receipts and private-check fields."""

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from experiments.horizon_votes import ROOT

KEY = ("case", "heading", "seat", "team", "condition")


def score(row):
    detour = row["case"] == "detour"
    expected = {
        "landing_distance": 3,
        "future_moves": 5 if detour else 2,
        "possible_if_approved": detour,
        "possible_if_rejected": not detour,
    }
    intended_vote = detour if row["team"] == "blue" else not detour
    facts = row["facts"]
    return {
        "cast": row["vote"] is not None,
        "vote": row["vote"] is intended_vote,
        "distance": facts.get("landing_distance") == 3,
        "budget": facts.get("future_moves") == expected["future_moves"],
        "branches": all(
            facts.get(k) is expected[k] for k in ("possible_if_approved", "possible_if_rejected")
        ),
        "all_facts": facts == expected,
    }


def report(root):
    with (root / "reason-codes.csv").open() as f:
        codes = {tuple(row[k] for k in KEY): row["decisive_reason"] for row in csv.DictReader(f)}
    arms = defaultdict(list)
    for name in ("choices.jsonl", "budget-rule.jsonl", "budget-count.jsonl"):
        for line in (root / name).read_text().splitlines():
            row = json.loads(line)
            key = tuple(str(row[k]) for k in KEY)
            results = score(row)
            results["justified_vote"] = results["vote"] and codes[key] == "yes"
            arms[row["condition"]].append(results)
    return {
        arm: {"n": len(rows), **{k: sum(r[k] for r in rows) for k in rows[0]}}
        for arm, rows in arms.items()
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", nargs="?", type=Path, default=ROOT / "move-budget")
    print(json.dumps(report(cli.parse_args().root), indent=2))
