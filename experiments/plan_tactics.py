"""Forced detour on a complete turn: four remaining moves and an all-closed hand."""

import argparse
import csv
import sys
from random import Random

from experiments.model_solitaire import label
from experiments.skill_probe import MODEL, optimistic_length
from experiments.turn_plans import plans, select
from footsteps.board import rotate
from footsteps.table import Table


def detour_table(sx, sy):
    trap = 8 if sx == 1 else 2
    detour = (4 if sy == 1 else 1) | (32 if sx == 1 else 128)
    table = Table(
        {
            "goal": [2 * sx, 0],
            "roles": ["good"],
            "hands": [[trap, detour]],
            "store": [0] * 4 + [255] * 2,
        },
        Random(0),
    )
    for pos, face in [([sx, 0], trap), ([0, sy], detour)]:
        table.commit({"kind": "draw", "tiles": [0, 0]})
        table.commit({"kind": "place", "at": pos, "tile": face, "rotation": 0})
        table.commit({"kind": "discard", "tile": 0})
        table.commit({"kind": "propose", "to": None})
    table.commit({"kind": "draw", "tiles": [0, 0]})
    table.started = True
    table.deadline = 60
    return table


def position(sx, sy):
    table = detour_table(sx, sy)
    state = table.game.view(0)
    state["draw_count"] = 2
    return state, table.choices(0, 0)


def viable(state, plan):
    # Evaluator only: the local policy cannot see this calculation.
    board = {tuple(p): f for p, f in state["board"]}
    b = plan["place"]
    board[tuple(b["at"])] = rotate(b["tile"], b["rotation"])
    dest = tuple(state["marker"] if plan["to"] is None else plan["to"])
    return optimistic_length(board, dest, tuple(state["goal"]), 3) is not None


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument("--local", action="store_true")
    args = cli.parse_args()
    w = csv.writer(sys.stdout, lineterminator="\n")
    w.writerow(["sx", "sy", "reverse", "plans", "possible", "index", "to", "possible_selected"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            state, opts = position(sx, sy)
            menu = plans(state, opts, local=args.local)
            rng = Random(f"fixture/{sx}/{sy}")
            rng.shuffle(menu)
            for reverse in (False, True):
                options = menu[::-1] if reverse else menu
                p = select(options, state, args.model, "model", rng, local=args.local)
                w.writerow(
                    [
                        sx,
                        sy,
                        reverse,
                        len(options),
                        sum(viable(state, q) for q in options),
                        options.index(p),
                        label(p["to"]),
                        viable(state, p),
                    ]
                )
                sys.stdout.flush()
