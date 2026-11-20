"""Audit saved cross-play games and summarize repeated presentations without a model server."""

import argparse
from collections import Counter
from pathlib import Path

from experiments.archive_rows import csv_rows, current_id
from experiments.behavior_crossplay import metrics
from experiments.behavior_probe import cases, tradeoffs
from experiments.social_summary import game_totals
from footsteps.record import read, replay


def rows(path):
    with path.open() as f:
        return list(csv_rows(f))


def audit(root):
    for path in sorted(root.glob("*.csv")):
        recorded = rows(path)
        dilemma = path.stem.startswith("dilemma-")
        positions = tradeoffs if dilemma else cases
        expected = [
            (name, s["seat"], s["state"]["role"], rev, p)
            for name, s, p in positions()
            for rev in (False, True)
        ]
        counts = Counter()
        for row, (name, seat, role, rev, pref) in zip(recorded, expected, strict=True):
            assert (name, str(seat), role, str(rev)) == tuple(
                row[k] for k in ("case", "seat", "role", "reverse")
            )
            assert row["preferred"] == ("" if pref is None else str(pref))
            if pref is not None:
                counts[name] += row["choice"] == str(pref)
            elif name == "quiet-opening":
                counts[f"pass/{role}"] += row["choice"] == ""
            elif name == "ordinary-move":
                counts["red approaches"] += row["choice"] == "True"
        print(path.stem, dict(counts))
    for path in sorted(root.glob("*/results.csv")):
        games = rows(path)
        records = {current_id(p.stem): p for p in path.parent.glob("*.json")}
        assert len(games) == len(records)
        counts = Counter()
        for row in games:
            seat, role = int(row["seat"]), row["role"]
            record = read(records[f"{row['seed']}-P{seat}-{role}"])
            assert replay(record).winner == row["winner"]
            assert record["setup"]["roles"][seat] == role
            for key, v in metrics(record, seat).items():
                assert row[key] == ("" if v is None else str(v))
            counts[f"{role} focal wins"] += role == row["winner"]
            counts[f"{role} focal survived"] += not row["removed_turn"]
        print(path.parent.name, dict(counts))
    for path in sorted(root.glob("*/choices.csv")):
        print(path.parent.name, dict(game_totals(path.parent)))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=Path)
    audit(cli.parse_args().root)
