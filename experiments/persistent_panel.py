"""Persistent-seat corridor and delayed-accusation experiments."""

import argparse
import json
from collections import Counter
from functools import partial
from pathlib import Path
from random import Random

from experiments.persistent_listener import opponents
from experiments.persistent_runtime import play_table
from footsteps.board import moves
from footsteps.game import with_exit_origin
from footsteps.record import read, starting_game
from footsteps.session import CONTEXT_WINDOWS, Session
from footsteps.solo import setup as solo_setup
from footsteps.table import Table


def corridor(heading, seconds=30):
    goal = {"north": [0, 2], "east": [2, 0], "south": [0, -2], "west": [-2, 0]}[heading]
    setup = with_exit_origin({"roles": ["blue"], "goal": goal, "hands": [[65]], "store": [65, 65]})
    return Table(setup, Random(103), seconds=seconds, discussion=0)


def report(root):
    record = read(root / "game.json")
    game = starting_game(record)
    solo = len(game.roles) == 1
    focal = 0 if solo else 3
    decisions, faults, first_steps = [], 0, []
    for i, event in enumerate(record["events"], 1):
        kind = event["kind"]
        if kind in ("move_vote", "eliminate_vote"):
            value = event["votes"][game.alive.index(focal)]
            decisions.append((i, game.turn, kind, value))
            faults += value is None
        elif (kind == "nominate" and game.queue[0] == focal) or (
            kind in ("place", "discard", "propose") and game.actor == focal
        ):
            decisions.append((i, game.turn, kind, {k: v for k, v in event.items() if k != "kind"}))
            faults += bool(event.get("timeout"))
        game.apply(event)
        if solo and kind == "place" and game.turn == 1:
            first_steps = moves(game.board, game.marker)
    assert game.winner
    calls = list(map(json.loads, (root / "calls.jsonl").read_text().splitlines()))
    print(root.name, game.winner, "turn", game.turn, "marker", game.marker)
    print("Seat decisions", decisions, "misses", faults)
    if solo:
        print("Legal landings after opening build", first_steps)
    print(
        "Calls",
        dict(Counter(r["tool"] for r in calls)),
        "errors",
        sum(r["error"] for r in calls),
        "prompt and reply tokens",
        sum(r["prompt_tokens"] or 0 for r in calls),
        sum(r["reply_tokens"] or 0 for r in calls),
        "inference seconds",
        round(sum(r["inference_seconds"] for r in calls), 1),
    )
    if not solo:
        print(
            "Compactions",
            [
                (r["revision"], r["forced_compaction"], r["error"])
                for r in calls
                if r["tool"] == "compact"
            ],
        )
        print(
            "Lookups",
            [
                (r["revision"], r["filters"], r["entry_ids"])
                for r in calls
                if r["tool"] == "history"
            ],
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "case", choices=("north", "east", "west", "south", "true", "false", "ordinary", "report")
    )
    parser.add_argument("--inspect-rotations", action="store_true")
    parser.add_argument("--movement-context", action="store_true")
    parser.add_argument(
        "--implicit-wait",
        action="store_true",
        help="use wait() anchored at the update the model saw",
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("private", type=Path, nargs="?")
    parser.add_argument("--seed", type=int, default=9811, help="ordinary solitaire deal")
    parser.add_argument("--decision-seconds", type=int, default=30)
    parser.add_argument("--context", type=int, choices=CONTEXT_WINDOWS, default=8192)
    parser.add_argument("--model", default="footsteps-qwen3.8:27b-rana-layout")
    args = parser.parse_args()
    if args.case == "report":
        report(args.output)
        raise SystemExit
    if args.private is None:
        parser.error("provide a fresh private trace path")
    if args.case in ("true", "false"):
        if args.inspect_rotations or args.movement_context:
            parser.error("use the frozen social interface for this comparison")
        setup = {
            "goal": [2, 0],
            "roles": ["blue", "blue", "red", "blue"],
            "hands": [[255], [9], [33], [0]],
            "store": [18, 12, 0],
        }
        play_table(
            args.output,
            args.private,
            args.model,
            Table(setup, Random(1), seconds=args.decision_seconds, discussion=15),
            3,
            opponents=lambda host, done: opponents(host, done, args.case == "false", delayed=True),
            context=args.context,
            session_class=partial(Session, wait_at_notice=args.implicit_wait),
            compact_when=lambda snap: (
                snap["state"]["turn"] == 1 and snap["state"]["nominator"] == 3
            ),
        )
    else:
        play_table(
            args.output,
            args.private,
            args.model,
            Table(
                with_exit_origin(solo_setup(args.seed, (3, 2), 2, 7, 0.55)),
                Random(f"draw/{args.seed}"),
                seconds=args.decision_seconds,
                discussion=0,
            )
            if args.case == "ordinary"
            else corridor(args.case, args.decision_seconds),
            0,
            context=args.context,
            session_class=partial(
                Session,
                inspect_rotations=args.inspect_rotations,
                movement_context=args.movement_context,
                wait_at_notice=args.implicit_wait,
            ),
        )

    report(args.output)
