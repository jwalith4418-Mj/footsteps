"""Run from the repo root with python -m experiments.run."""

import argparse
import csv
from itertools import product
from pathlib import Path

from footsteps.solo import POLICIES, setup, simulate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=200)
    parser.add_argument("--out", type=Path, default=Path("experiments/pilot.csv"))
    args = parser.parse_args()
    if args.seeds <= 0:
        parser.error("--seeds must be positive")
    with args.out.open("w", newline="") as f:
        writer = None
        for goal, store, hand in product([(6, 0), (4, 2)], [6, 10], [2, 4]):
            for seed in range(args.seeds):
                initial = setup(seed, goal, hand, store, 0.55)
                for policy in POLICIES:
                    r, _ = simulate(initial, seed, policy)
                    row = dict(
                        goal_x=goal[0], goal_y=goal[1], store=store, hand=hand, density=0.55, **r
                    )
                    if writer is None:
                        writer = csv.DictWriter(f, fieldnames=list(row), lineterminator="\n")
                        writer.writeheader()
                    writer.writerow(row)


if __name__ == "__main__":
    main()
