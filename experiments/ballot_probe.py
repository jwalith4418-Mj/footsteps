"""Counterbalance option order on frozen seat views. Only the host reads the record."""

import argparse
import csv
import sys
from pathlib import Path
from random import Random

from footsteps.board import distance
from footsteps.ollama import infer
from footsteps.record import read
from footsteps.solo import sealed
from footsteps.table import BALLOTS, Table

SOURCE = Path(__file__).with_name("model-panel") / "llama-guided-11/game.json"


def view_before_vote(table, seat):
    state = table.game.view(seat)
    if seat not in state["alive"] or state["stage"] not in BALLOTS:
        raise ValueError("a living seat must have a pending ballot")
    return {
        "seat": seat,
        "state": state,
        "history": table.history[seat].copy(),
        "choices": {"vote": [True, False]},
    }


def positions():
    record = read(SOURCE)
    table = Table(record["setup"], Random(0))
    for n, event in enumerate(record["events"], 1):
        if n in (14, 25, 30, 35, 40, 44):
            yield f"record-e{n}", view_before_vote(table, 3), None
        table.commit(event)

    # Red P0 builds a dead end to the east. North goes directly to the open EXIT.
    setup = {"goal": [0, 1], "roles": ["red", "blue"], "hands": [[8], [9]], "store": [16, 32]}
    for case, destination in [("exit", [0, 1]), ("trap", [1, 0]), ("eliminate-blue", None)]:
        table = Table(setup, Random(0))
        for event in [
            {"kind": "draw", "tiles": [16, 32]},
            {"kind": "place", "at": [1, 0], "tile": 8, "rotation": 0},
            {"kind": "discard", "tile": 16},
            {"kind": "propose", "to": destination},
        ]:
            table.commit(event)
        if destination is None:
            table.commit({"kind": "nominate", "target": None})  # P1 passes
            table.commit({"kind": "nominate", "target": 1})  # P0 nominates P1
        for seat in (0, 1):
            blue = setup["roles"][seat] == "blue"
            yield case, view_before_vote(table, seat), blue if case == "exit" else not blue


def preview(snapshot):
    """Describe the two group outcomes using only facts available to this seat."""
    state = snapshot["state"]
    pending = state["pending"]
    if state["stage"] == "move_vote":
        goal = tuple(state["goal"])
        board = {tuple(pos): face for pos, face in state["board"]}

        def outcome(pos):
            pos = tuple(pos)
            if pos == goal:
                return "the marker reaches EXIT and blue wins"
            if not state["store_count"]:
                return "the store is empty and red wins"
            if sealed(board, pos, goal):
                return "the marker can never reach EXIT from this square"
            return f"the marker is {distance(pos, goal)} steps from EXIT by Manhattan distance"

        yes, no = outcome(pending), outcome(state["marker"])
    else:
        remaining = [p for p in state["alive"] if p != pending]
        yes = f"P{pending} is eliminated and seats {remaining} survive"
        if (
            state["role"] == "red"
            and set(remaining) <= {snapshot["seat"], *state["teammates"]}
            or (
                pending == snapshot["seat"]
                and state["role"] == "blue"
                and state["player_count"] - state["red_count"] == 1
            )
        ):
            yes += ", so no blue seat remains and red wins"
        no = f"P{pending} remains alive"
    return f"If approved, {yes}. If rejected, {no}."


def run(models, out, with_preview=False):
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(("model", "case", "seat", "encoding", "first", "preferred", "choice"))
    for model in models:
        for case, snapshot, preferred in positions():
            for first in (True, False):
                snap = {**snapshot, "choices": {"vote": [first, not first]}}
                if with_preview:
                    # Keep the same twelve history entries, appending the factual cue to the last.
                    history = snap["history"].copy()
                    history[-1] = {
                        **history[-1],
                        "text": history[-1]["text"] + "\nVote preview: " + preview(snap),
                    }
                    snap["history"] = history
                for named in (True,) if with_preview else (False, True):
                    vote = infer(snap, model, 15, guided=True, named_ballots=named, no_think=True)[
                        "vote"
                    ]
                    writer.writerow(
                        (
                            model,
                            case,
                            snap["seat"],
                            "preview" if with_preview else ("named" if named else "index"),
                            first,
                            preferred,
                            vote,
                        )
                    )
                    out.flush()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--models", nargs="+", default=["llama3.1:8b", "qwen3.5:4b"])
    cli.add_argument("--preview", action="store_true")
    args = cli.parse_args()
    run(args.models, sys.stdout, args.preview)
