"""Test the two placement gates on Blue's last viable build and the guest's Red trap."""

import argparse
import csv
import io
import json
from itertools import product
from pathlib import Path

from experiments.action_probe import GUEST, ROOT, position
from experiments.skill_probe import MODEL
from footsteps.board import moves, optimistic_length, rotate
from footsteps.ollama import infer
from footsteps.solo import sealed


def trial(rows, case, mode, reverse, snap, forced=None, *, joint):
    opts = snap["choices"].copy()
    if forced:
        opts.update({k: [v] for k, v in forced.items()})
    if reverse:
        opts = {k: vs[::-1] for k, vs in opts.items()}
    attempts = []
    try:
        picked = infer(
            {**snap, "choices": opts},
            MODEL,
            30,
            guided=not forced,
            explicit_actions=True,
            no_think=True,
            note_file=io.StringIO(),
            placement_attempts=attempts,
            joint_placement=joint,
        )
    except ValueError:
        if not attempts or not attempts[-1][1]:
            raise
        picked = None
    if not attempts:
        attempts.append((picked, None))
    state = snap["state"]
    for attempt, (choice, error) in enumerate(attempts, 1):
        tactical = ""
        if not error and not forced:
            board = dict(state["board"])
            board[tuple(choice["at"])] = rotate(choice["tile"], choice["rotation"])
            marker, goal = state["marker"], state["goal"]
            tactical = (
                sealed(board, marker, goal)
                if state["role"] == "red"
                else any(
                    optimistic_length(board, step, goal, state["store_count"] + 1) is not None
                    for step in moves(board, marker)
                )
            )
        rows.writerow(
            [case, mode or "ordinary", reverse, attempt, json.dumps(choice), error or "", tactical]
        )


def run(output, joint):
    blue = ROOT / "exit-origin/social/8602-red1+3.json"
    with output.open("x") as f:
        rows = csv.writer(f, lineterminator="\n")
        rows.writerow(
            ["case", "mode", "reverse", "attempt", "choice", "rejection", "tactical_success"]
        )
        for case, path, rev, seat in (("blue-route", blue, 41, 4), ("red-trap", GUEST, 23, 2)):
            for mode, reverse in product((None, "edge", "edge-and-marker"), (False, True)):
                trial(
                    rows,
                    case,
                    mode,
                    reverse,
                    position(path, rev, seat, placement_check=mode),
                    joint=joint,
                )
                f.flush()
        for remote, closed in product((False, True), repeat=2):
            origin = (-2, -1 if remote else -2)
            fixed = {"origin": origin, "at": (-1, origin[1]), "tile": 58, "rotation": int(closed)}
            case = f"{'remote' if remote else 'marker'}-{'closed' if closed else 'open'}"
            for mode in ("edge", "edge-and-marker"):
                # Each coordinate and face index now has a single legal value. The two judgments remain free.
                trial(
                    rows,
                    case,
                    mode,
                    False,
                    position(blue, 41, 4, placement_check=mode),
                    fixed,
                    joint=joint,
                )
                f.flush()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("csv", type=Path)
    cli.add_argument(
        "--joint", action="store_true", help="ask for all five or six fields in one model reply"
    )
    args = cli.parse_args()
    run(args.csv, args.joint)
