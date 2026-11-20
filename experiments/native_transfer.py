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


def transfer_panel():
    kit = fixed_kit(Random(8700), 16, 29, 29)
    count = 0
    for seed in range(9600, 9700):
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
                    for team in ("good", "bad")
                }
                if all(0 < n <= len(actions) // 3 for n in goals.values()):
                    for idx, team in enumerate(("good", "bad")):
                        setup = with_exit_origin(record["setup"])
                        ox, oy = record["setup"]["goal"]
                        roles = ["good"] * 4
                        roles[game.actor if idx else (game.actor + 1) % 4] = "bad"
                        t = Table({**setup, "roles": roles}, Random(0), color_teams=True)
                        t.started = True
                        for old in record["events"][:rev]:
                            e = old.copy()
                            for key in ("at", "to"):
                                if e.get(key) is not None:
                                    x, y = e[key]
                                    e[key] = [x - ox, y - oy]
                            t.commit(e)
                        t.deadline = 60
                        yield f"held-{seed}-E{rev}-{team}", t.view(game.actor, 0), "", None
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
    args = p.parse_args()
    run(args.output, args.model, args.arms, False, panels=transfer_panel(), paired_order=True)
