"""Blind paired Blue and Red builders to one another on fresh cooperative prefixes."""

import argparse
from itertools import product
from pathlib import Path
from random import Random

from experiments.native_probe import run
from experiments.offsets import trial
from experiments.rotation_probe import success
from experiments.skill_probe import MODEL
from footsteps.board import frontier
from footsteps.game import Game, with_exit_origin
from footsteps.table import Table, fixed_kit


def transfer_panel(*, isolate_square=False, start_seed=9600):
    kit = fixed_kit(Random(8700), 16, 29, 29)
    count = 0
    for seed in range(start_seed, start_seed + 100):
        _, record = trial((3, 2), seed, "route", kit=kit)
        game = Game(record["setup"])
        for rev, event in enumerate(record["events"]):
            if game.stage == "place" and game.last_draw == 2:
                view = game.view(game.actor)
                actions = list(
                    product(set(view["hand"]), range(4), frontier(game.board, game.goal))
                )
                goals = {
                    team: sum(success({**view, "role": team}, *a, None) for a in actions)
                    for team in ("blue", "red")
                }
                if all(0 < n <= len(actions) // 3 for n in goals.values()):
                    for idx, team in enumerate(("blue", "red")):
                        setup = with_exit_origin(record["setup"])
                        ox, oy = record["setup"]["goal"]
                        roles = ["blue"] * 4
                        roles[game.actor if idx else (game.actor + 1) % 4] = "red"
                        t = Table({**setup, "roles": roles}, Random(0))
                        t.started = True
                        for old in record["events"][:rev]:
                            e = old.copy()
                            for key in ("at", "to"):
                                if e.get(key) is not None:
                                    x, y = e[key]
                                    e[key] = [x - ox, y - oy]
                            t.commit(e)
                        t.deadline = 60
                        snap = t.view(game.actor, 0)
                        if isolate_square:
                            # Diagnostic intervention. Only admit floors where both teams'
                            # successful actions all use this same square.
                            squares = {
                                at
                                for face, rot, at in actions
                                if any(
                                    success({**view, "role": role}, face, rot, at, None)
                                    for role in goals
                                )
                            }
                            if len(squares) != 1:
                                raise ValueError("no unique shared tactical square")
                            x, y = next(iter(squares))
                            snap["choices"]["at"] = [(x - ox, y - oy)]
                        yield f"held-{seed}-E{rev}-{team}", snap, "", None
                    count += 1
                    break
            game.apply(event)
        if count == 4:
            return
    raise ValueError("insufficient qualifying deals")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--model", default=MODEL)
    p.add_argument("--arms", nargs="+", default=["menu", "direct", "hand"])
    p.add_argument(
        "--isolate-square",
        action="store_true",
        help="offer only the shared tactical square to both teams",
    )
    args = p.parse_args()
    run(
        args.output,
        args.model,
        args.arms,
        False,
        panels=transfer_panel(isolate_square=args.isolate_square),
        paired_order=True,
    )
