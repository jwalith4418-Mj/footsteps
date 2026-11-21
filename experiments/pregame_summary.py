"""Summarize matched pregame-note trials from the shareable receipts."""

import argparse
import json
from collections import defaultdict
from itertools import groupby
from operator import itemgetter
from pathlib import Path

from experiments.horizon_summary import score


def summarize(root):
    groups = defaultdict(list)
    for path in sorted(root.glob("*-ballots.jsonl")):
        for line in path.read_text().splitlines():
            row = json.loads(line)
            groups[row["model"], row["cue"], row["seed"]].append(row)
    results = []
    positions = {
        (case, heading, team)
        for case in ("short", "detour")
        for heading in ("west", "north")
        for team in ("blue", "red")
    }
    for (model, cue, seed), rows in sorted(groups.items()):
        indexed = {(r["case"], r["heading"], r["team"]): score(r) for r in rows}
        if len(rows) != len(positions) or indexed.keys() != positions:
            raise ValueError(f"Incomplete or duplicated ballot panel for {model} {cue} {seed}")
        both_teams = sum(
            all(indexed[case, heading, team]["vote"] for team in ("blue", "red"))
            for case in ("short", "detour")
            for heading in ("west", "north")
        )
        results.append(
            {
                "model": model,
                "cue": cue,
                "seed": seed,
                "both_teams": both_teams,
                "yes": sum(r["vote"] is True for r in rows),
                **{
                    field: sum(result[field] for result in indexed.values())
                    for field in ("cast", "vote", "budget", "branches", "all_facts")
                },
            }
        )
    return results


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument(
        "root", type=Path, nargs="?", default=Path(__file__).parent / "pregame-analysis"
    )
    panels = summarize(cli.parse_args().root)
    for (model, cue), group in groupby(panels, key=itemgetter("model", "cue")):
        rows = list(group)
        print(
            json.dumps(
                {
                    "model": model,
                    "cue": cue,
                    "ballots": 8 * len(rows),
                    "votes_per_seed": [r["vote"] for r in rows],
                    **{
                        key: sum(r[key] for r in rows)
                        for key in (
                            "cast",
                            "yes",
                            "vote",
                            "both_teams",
                            "budget",
                            "branches",
                            "all_facts",
                        )
                    },
                }
            )
        )
