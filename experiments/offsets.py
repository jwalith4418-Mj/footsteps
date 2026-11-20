"""Matched four-seat exit-offset trial on the sixteen printed tiles (issue 15)."""

import argparse
import csv
import json
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from random import Random
from statistics import median

from footsteps.board import OPEN, START, frontier, moves, rotate
from footsteps.game import Game
from footsteps.record import new_record
from footsteps.solo import best, movement, placement
from footsteps.table import PAPER_KIT as KIT

GOALS = (
    (1, 0),
    (2, 0),
    (1, 1),
    (3, 0),
    (2, 1),
    (4, 0),
    (3, 1),
    (2, 2),
    (3, 2),
    (4, 2),
    (6, 0),
    (4, 4),
    (9, 0),
)
POLICIES = ("exits", "route")
DATA = Path(__file__).with_name("offsets.csv")


def deal(seed, goal, kit=KIT):
    tiles = list(kit)
    Random(f"deal/{seed}").shuffle(tiles)
    return {
        "goal": list(goal),
        "roles": ["good"] * 4,
        "hands": [tiles[i : i + 2] for i in range(0, 8, 2)],
        "store": tiles[8:],
    }


def trial(goal, seed, policy, *, kit=KIT, rotations=range(4)):
    initial = deal(seed, goal, kit)
    game = Game(initial)
    record = new_record(initial)
    draw_rng = Random(f"draw/{seed}")
    choice_rng = Random(f"choices/{seed}")

    play_out(game, record, policy, draw_rng, choice_rng, rotations=rotations)
    return {
        "x": goal[0],
        "y": goal[1],
        "seed": seed,
        "policy": policy,
        "win": int(game.winner == "good"),
        "turns": game.turn,
    }, record


def play_out(game, record, policy, draw_rng, choice_rng, *, rotations=range(4)):
    """Complete a cooperative trajectory starting at a draw, using each builder’s private view."""

    def act(kind, **kwargs):
        event = dict(kind=kind, **kwargs)
        game.apply(event)
        record["events"].append(event)

    while not game.winner:
        act("draw", tiles=draw_rng.sample(game.store, min(2, len(game.store))))
        view = game.view(game.actor)
        board = dict(view["board"])
        p, face, rotation = placement(
            board,
            view["marker"],
            view["goal"],
            view["hand"],
            policy,
            choice_rng,
            rotations=rotations,
        )
        act("place", at=list(p), tile=face, rotation=rotation)
        if game.stage == "discard":
            hand = sorted(set(game.view(game.actor)["hand"]))
            act("discard", tile=best(hand, lambda f: -f.bit_count(), choice_rng))
        view = game.view(game.actor)
        destination = movement(
            dict(view["board"]), view["marker"], view["goal"], policy, choice_rng
        )
        act("propose", to=None if destination == view["marker"] else list(destination))
        if game.stage == "move_vote":
            act("move_vote", votes=[True] * len(view["alive"]))
        while game.stage == "nominate":
            act("nominate", target=None)


def opening_bridges(goal):
    """Enumerate first-builder four-tile holdings, counting each physical copy separately."""
    board = {START: OPEN, goal: OPEN}
    usable = set()
    for face in set(KIT):
        for p in frontier(board, goal):
            for rotation in range(4):
                floor = {**board, p: rotate(face, rotation)}
                if p in moves(floor, START) and goal in moves(floor, p):
                    usable.add(face)
    counts = Counter(any(face in usable for face in hand) for hand in combinations(KIT, 4))
    return counts[True], counts.total()


def sweep(out):
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=("x", "y", "seed", "policy", "win", "turns"), lineterminator="\n"
        )
        writer.writeheader()
        for goal in GOALS:
            for seed in range(1000, 1200):
                for policy in POLICIES:
                    row, _ = trial(goal, seed, policy)
                    writer.writerow(row)


def summary(path):
    groups = defaultdict(list)
    with path.open() as f:
        for row in csv.DictReader(f):
            groups[int(row["x"]), int(row["y"]), row["policy"]].append(row)
    print(
        "| Exit | Policy | Games | Wins | Wins on shortest time | Wins before P3 builds | Median winning turn |"
    )
    print("|---|---|---:|---:|---:|---:|---:|")
    for x, y in GOALS:
        for policy in POLICIES:
            group = groups[x, y, policy]
            turns = [int(row["turns"]) for row in group if int(row["win"])]
            med = f"{median(turns):g}" if turns else "—"
            print(
                f"| ({x}, {y}) | {policy} | {len(group)} | {len(turns)} | "
                f"{turns.count(x + y)} | {sum(t < 4 for t in turns)} | {med} |"
            )
    for goal in ((2, 0), (1, 1)):
        yes, total = opening_bridges(goal)
        print(f"\nOpening hands that can bridge {goal}: {yes}/{total}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    run = sub.add_parser("run")
    run.add_argument("--out", type=Path, default=DATA)
    report = sub.add_parser("summary")
    report.add_argument("path", type=Path, nargs="?", default=DATA)
    example = sub.add_parser("record")
    example.add_argument("--goal", type=int, nargs=2, required=True)
    example.add_argument("--seed", type=int, required=True)
    example.add_argument("--policy", choices=POLICIES, required=True)
    example.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "run":
        sweep(args.out)
    elif args.mode == "summary":
        summary(args.path)
    else:
        _, record = trial(tuple(args.goal), args.seed, args.policy)
        args.out.write_text(json.dumps(record, indent=2) + "\n")


if __name__ == "__main__":
    main()
