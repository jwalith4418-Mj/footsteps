"""Vary order and answer encoding at the first proposal of two recorded guided games."""

import argparse
import csv
import sys
from pathlib import Path
from random import Random

from footsteps.board import neighbors
from footsteps.ollama import infer
from footsteps.record import read
from footsteps.table import Table


def first_proposal(panel, seed):
    record = read(panel / f"qwen-guided-{seed}" / "game.json")
    table = Table(record["setup"], Random(f"draw/{seed}"), seconds=15, discussion=0)
    for seat in range(4):
        table.join(seat, 0)
    for event in record["events"][1:3]:
        table.submit(0, table.revision, {k: v for k, v in event.items() if k != "kind"}, 0)
    if table.record["events"] != record["events"][:3] or table.game.stage != "propose":
        raise ValueError("failed to reconstruct the recorded first proposal")
    return table.view(0, 0)


def run(panel, models, no_think):
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(["model", "seed", "encoding", "first_option", "picked"])
    for model in models:
        for seed in (11, 12):
            snapshot = first_proposal(panel, seed)
            directions = dict(
                zip(neighbors(snapshot["state"]["marker"]), ("north", "east", "south", "west"))
            )
            options = snapshot["choices"]["to"]
            for values in (options, list(reversed(options))):
                snap = {**snapshot, "choices": {"to": values}}
                names = ["stay" if p is None else directions[tuple(p)] for p in values]
                for encoding in ("indices", "names"):
                    dest = infer(
                        snap,
                        model,
                        15,
                        guided=True,
                        named_moves=encoding == "names",
                        no_think=no_think,
                    )["to"]
                    writer.writerow([model, seed, encoding, names[0], names[values.index(dest)]])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("panel", type=Path)
    parser.add_argument("--models", nargs="+", default=["qwen2.5:3b", "llama3.1:8b"])
    parser.add_argument("--no-think", action="store_true")
    args = parser.parse_args()
    run(args.panel, args.models, args.no_think)
