"""Compare cooperative tables on the printed kit and randomized physical orientations."""

import argparse
import csv
import json
from pathlib import Path
from random import Random

from experiments.offsets import POLICIES, trial
from experiments.tile_density import GOAL, build_options
from footsteps.board import distance, moves, rotate
from footsteps.game import Game
from footsteps.table import PAPER_KIT


def observations(record, fixed):
    game = Game(record["setup"])
    needed = no_build = lost_to_fixed = 0
    first_miss = None
    for event in record["events"]:
        if event["kind"] == "place":
            assert not fixed or event["rotation"] == 0
            view = game.view(game.actor)
            free = build_options(view)
            printed = build_options(view, (0,))
            if game.turn == 1:
                opening = printed if fixed else free
            if all(
                distance(q, game.goal) >= distance(game.marker, game.goal)
                for q in moves(game.board, game.marker)
            ):
                needed += 1
                lost_to_fixed += bool(free and not printed)
                if not (printed if fixed else free):
                    no_build += 1
                    if first_miss is None:
                        first_miss = game.turn
        game.apply(event)
    return {
        "opening_options": opening,
        "needed": needed,
        "no_forward_build": no_build,
        "first_miss": first_miss,
        "rotation_only_hands": lost_to_fixed,
    }


def run(root, n):
    root.mkdir(exist_ok=False)
    saved = False
    with (root / "deals.csv").open("w") as f:
        rows = None
        for seed in range(9400, 9400 + n):
            rng = Random(f"reprint/{seed}")
            for name, kit in (
                ("printed", PAPER_KIT),
                ("reprinted", [rotate(t, rng.randrange(4)) for t in PAPER_KIT]),
            ):
                for policy in POLICIES:
                    outcomes = {}
                    for arm, rotations in (("rotate", range(4)), ("fixed", (0,))):
                        score, record = trial(GOAL, seed, policy, kit=kit, rotations=rotations)
                        row = {
                            **score,
                            "kit": name,
                            "arm": arm,
                            **observations(record, arm == "fixed"),
                        }
                        if rows is None:
                            rows = csv.DictWriter(f, row, lineterminator="\n")
                            rows.writeheader()
                        rows.writerow(row)
                        outcomes[arm] = score["win"], record
                    if (
                        not saved
                        and name == "printed"
                        and outcomes["rotate"][0]
                        and not outcomes["fixed"][0]
                    ):
                        for arm, (_, rec) in outcomes.items():
                            (root / f"{seed}-{policy}-{arm}.json").write_text(
                                json.dumps(rec, separators=(",", ":")) + "\n"
                            )
                        saved = True


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("out", type=Path)
    cli.add_argument("--deals", type=int, default=128)
    args = cli.parse_args()
    run(args.out, args.deals)
