"""Matched complete games with a menu control, native commits, and a private rotatable hand."""

import argparse
import json
import secrets
from http.client import HTTPException
from pathlib import Path
from random import Random
from time import monotonic

from experiments.skill_probe import MODEL
from experiments.social_evidence import social_deal
from experiments.social_prompt import advocate
from footsteps.action_tools import native_decision
from footsteps.decision_notes import open_private
from footsteps.game import with_exit_origin
from footsteps.ollama import infer
from footsteps.record import replay
from footsteps.table import Table, fixed_kit


def game(root, private, seed, model, arm, scope, *, corridor=None, give_opening=False):
    key = f"{seed}-{arm}-{scope}"
    if corridor:
        key = f"corridor-{corridor}-{key}"
        if give_opening:
            key = f"guided-{key}"
        roles = ["blue"]
        goal = {"east": [2, 0], "north": [0, 2]}[corridor]
        setup = {"roles": roles, "goal": goal, "hands": [[65]], "store": [65, 65]}
    else:
        roles = ["blue", "red", "blue", "blue"]
        setup = social_deal(seed, roles, fixed_kit(Random(8700), 16, 29, 29))
        setup["goal"] = [2, 2]
    t = Table(with_exit_origin(setup), Random(f"draw/{seed}"), discussion=1)
    t.record["table_id"] = secrets.token_hex(16)
    for seat in range(len(roles)):
        t.join(seat, 0)
    play(t, key, root, private, model, arm, scope, corridor=corridor, give_opening=give_opening)


def play(
    t,
    key,
    root,
    private,
    model,
    arm,
    scope,
    *,
    corridor=None,
    give_opening=False,
    floor_policy=None,
    removal_policy=None,
):
    speaker = None
    with (
        open_private(private / f"{key}.jsonl") as notes,
        (root / f"{key}.calls.jsonl").open("x") as traces,
    ):
        while not t.game.winner:
            now = t.opens
            stage = t.game.stage
            revision = t.revision
            if stage == "eliminate_vote":
                snap = t.view(speaker, now - t.discussion)
                try:
                    text = advocate(snap, model, explicit_actions=True)
                except (OSError, HTTPException, ValueError):
                    text = ""
                if text:
                    t.say(speaker, revision, text, now - t.discussion)
            missed = False
            for seat in range(len(t.game.roles)):
                if t.revision != revision:
                    break
                snap = t.view(seat, now)
                if not snap["choices"]:
                    continue
                snap["table_id"] = t.record["table_id"]
                native = arm != "menu" and (stage == "place" or scope == "all")
                log = []
                started = monotonic()
                status = "accepted"
                interface = arm if native else "menu"
                try:
                    if floor_policy is not None and stage in ("place", "propose", "move_vote"):
                        interface = arm
                        choice = floor_policy(snap, model, notes, log)
                    elif removal_policy is not None and stage == "eliminate_vote":
                        interface = "relative-binary"
                        choice = removal_policy(snap, model, notes, log)
                    elif native:

                        def orient(handle, turns, seat=seat, revision=revision, now=now):
                            t.orient(seat, revision, handle, turns, now)

                        task = None
                        if give_opening and t.game.turn == 1 and stage == "place":
                            rotation, square = (3, [-1, 0]) if corridor == "east" else (2, [0, -1])
                            task = f"A winning plan starts by placing the straight at {square} with absolute rotation {rotation}. Choose your actual placement."
                        choice = native_decision(
                            snap,
                            model,
                            30,
                            mode=arm,
                            orient=orient,
                            trace=log,
                            note_file=notes,
                            task=task,
                        )
                    else:
                        choice = infer(
                            snap,
                            model,
                            30,
                            no_think=True,
                            explicit_actions=True,
                            named_moves=True,
                            named_ballots=True,
                            note_file=notes,
                        )
                    if monotonic() - started >= 30:
                        raise TimeoutError("late reply")
                except (ValueError, OSError, HTTPException) as exc:
                    missed = True
                    status = str(exc)
                else:
                    if stage == "nominate" and choice["target"] is not None:
                        speaker = seat
                    t.submit(seat, revision, choice, now)
                traces.write(
                    json.dumps(
                        {
                            "turn": snap["state"]["turn"],
                            "seat": seat,
                            "revision": revision,
                            "stage": stage,
                            "interface": interface,
                            "status": status,
                            "seconds": round(monotonic() - started, 3),
                            "calls": log,
                        },
                        separators=(",", ":"),
                    )
                    + "\n"
                )
                traces.flush()
            if missed and t.revision == revision:
                t.tick(t.deadline)
    assert replay(t.record).winner == t.game.winner
    with (root / f"{key}.json").open("x") as f:
        json.dump(t.record, f, separators=(",", ":"))
        f.write("\n")
    print(key, t.game.winner, t.game.turn, t.game.marker, flush=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=Path)
    cli.add_argument("private", type=Path)
    cli.add_argument("--seeds", type=int, nargs="+", default=[9501])
    cli.add_argument(
        "--arms", choices=("menu", "direct", "hand"), nargs="+", default=("menu", "direct", "hand")
    )
    cli.add_argument("--scope", choices=("build", "all"), default="build")
    cli.add_argument("--model", default=MODEL)
    cli.add_argument(
        "--corridor",
        choices=("east", "north"),
        help="two-turn solitaire corridor with a directed straight in hand",
    )
    cli.add_argument(
        "--give-opening",
        action="store_true",
        help="supply the winning first placement in the solitaire hand control",
    )
    args = cli.parse_args()
    if args.give_opening and (not args.corridor or args.arms != ["hand"]):
        cli.error("--give-opening requires a corridor and --arms hand")
    args.root.mkdir(exist_ok=True, parents=True)
    args.private.mkdir(exist_ok=True, parents=True)
    for seed in args.seeds:
        for arm in args.arms:
            game(
                args.root,
                args.private,
                seed,
                args.model,
                arm,
                args.scope,
                corridor=args.corridor,
                give_opening=args.give_opening,
            )
