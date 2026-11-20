"""Paired bit thresholds in the four-seat paper game, with rotation and private hands."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from random import Random

from experiments.offsets import POLICIES, trial
from footsteps.board import connects, distance, moves, neighbors, rotate
from footsteps.game import Game
from footsteps.solo import exits, sealed, setup
from footsteps.table import PAPER_KIT, fixed_kit

GOAL = (4, 2)


def kit(seed, p):
    initial = setup(seed, GOAL, 2, 14, p)
    return initial["hands"][0] + initial["store"]


def build_options(state):
    board = dict(state["board"])
    marker, goal = state["marker"], state["goal"]
    results = set()
    for d, q in enumerate(neighbors(marker)):
        if q in board or distance(q, goal) >= distance(marker, goal):
            continue
        for tile in state["hand"]:
            for rotation in range(4):
                face = rotate(tile, rotation)
                if connects(board[marker], face, d) and exits(board, q, face, goal) == 2:
                    results.add((q, face))
    return len(results)


def observations(record):
    g = Game(record["setup"])
    openings = needed = without = waits = 0
    for e in record["events"]:
        if g.stage == "place":
            view = g.view(g.actor)
            if not any(
                distance(q, g.goal) < distance(g.marker, g.goal) for q in moves(g.board, g.marker)
            ):
                choices = build_options(view)
                needed += 1
                without += choices == 0
                if g.turn == 1:
                    openings = choices
        waits += e["kind"] == "propose" and e["to"] is None
        g.apply(e)
    return {
        "opening_options": openings,
        "needed": needed,
        "no_forward_build": without,
        "waits": waits,
        "sealed": int(sealed(g.board, g.marker, g.goal)),
    }


def run(root, fixed=False):
    root.mkdir(parents=True, exist_ok=False)
    assert tuple(kit(0, 0.55)) == PAPER_KIT
    examples = set()
    with (root / "deals.csv").open("w") as f:
        writer = None
        fresh = range(8700, 8800)
        for k in fresh if fixed else [0, *fresh]:
            if fixed:
                mixes = {
                    f"{i}/{o}": fixed_kit(Random(k), 16, i, o)
                    for i, o in ((35, 35), (29, 29), (32, 26))
                }
            else:
                mixes = {str(p): kit(k, p) for p in (0.55, 0.45)}
            high, low, *_ = mixes.values()
            assert all((lo & hi) == lo for hi, lo in zip(high, low, strict=True))
            seeds = range(9000, 9200) if k == 0 else range(k * 8, k * 8 + 8)
            for seed in seeds:
                for policy in POLICIES:
                    records = []
                    for p, tiles in mixes.items():
                        outcome, record = trial(GOAL, seed, policy, kit=tiles)
                        records.append((outcome["win"], record))
                        row = {
                            "kit_seed": k,
                            "deal": seed,
                            "policy": policy,
                            "p": p,
                            "bits": sum(t.bit_count() for t in tiles),
                            "win": outcome["win"],
                            "turns": outcome["turns"],
                            **observations(record),
                        }
                        if writer is None:
                            writer = csv.DictWriter(f, row, lineterminator="\n")
                            writer.writeheader()
                        writer.writerow(row)
                    key = (records[0][0], records[1][0])
                    if (
                        (k == 0 or fixed)
                        and policy == "exits"
                        and key[0] != key[1]
                        and key not in examples
                    ):
                        examples.add(key)
                        for p, (_, record) in zip(mixes, records, strict=True):
                            p = p.replace("0.", "").replace("/", "-")
                            (root / f"deal-{seed}-p{p}.json").write_text(
                                json.dumps(record, separators=(",", ":")) + "\n"
                            )


def summary(path):
    groups = defaultdict(list)
    with path.open() as f:
        for r in csv.DictReader(f):
            groups[("printed" if r["kit_seed"] == "0" else "fresh", r["policy"])].append(r)
    for key, rows in groups.items():
        by_deal = defaultdict(dict)
        for r in rows:
            by_deal[r["kit_seed"], r["deal"]][r["p"]] = int(r["win"])
        labels = list(next(iter(by_deal.values())))
        for comparison in labels[1:]:
            print(
                *key,
                "win pair",
                labels[0],
                comparison,
                dict(Counter((d[labels[0]], d[comparison]) for d in by_deal.values())),
            )
        for p in labels:
            rs = [r for r in rows if r["p"] == p]
            totals = {
                k: sum(int(r[k]) for r in rs)
                for k in ("win", "opening_options", "needed", "no_forward_build", "sealed")
            }
            print(
                p,
                len(rs),
                "wins",
                totals["win"],
                "turn-six wins",
                sum(r["win"] == "1" and r["turns"] == "6" for r in rs),
                "opening choices",
                round(totals["opening_options"] / len(rs), 2),
                "no opening",
                sum(r["opening_options"] == "0" for r in rs),
                "no forward build",
                totals["no_forward_build"],
                "/",
                totals["needed"],
                "sealed",
                totals["sealed"],
            )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("mode", choices=("run", "summary"))
    cli.add_argument("path", type=Path)
    cli.add_argument("--fixed", action="store_true", help="sample exact incoming/outgoing totals")
    args = cli.parse_args()
    if args.mode == "run":
        run(args.path, args.fixed)
    else:
        summary(args.path)
