"""Counterbalance two complete legal placements on identical frozen seat views."""

import argparse
import csv
import json
import sys
from pathlib import Path
from random import Random

from footsteps.board import connects, distance, neighbors, rotate
from footsteps.ollama import RULES, model_request, request, tile
from footsteps.record import read
from footsteps.solo import exits, sealed
from footsteps.table import Table


def menu(state, choices):
    board = {tuple(p): f for p, f in state["board"]}
    marker, goal = tuple(state["marker"]), tuple(state["goal"])
    squares = set(map(tuple, choices["at"]))
    for direction, pos in enumerate(neighbors(marker)):
        if pos not in squares or distance(pos, goal) >= distance(marker, goal):
            continue
        pair = {}
        for face in choices["tile"]:
            for rotation in choices["rotation"]:
                oriented = rotate(face, rotation)
                if not connects(board[marker], oriented, direction):
                    continue
                after = {**board, pos: oriented}
                if sealed(after, pos, goal):
                    label = "trap"
                elif exits(after, pos, oriented, goal) == 2:
                    label = "onward"
                else:
                    continue
                pair.setdefault(label, {"tile": face, "rotation": rotation, "at": list(pos)})
        if len(pair) == 2:
            return pair
    return None


def snapshot_at(record, index, role):
    builder = Table(record["setup"], Random(0))
    for event in record["events"][:index]:
        builder.commit(event)
    seat = builder.game.actor
    roles = record["setup"]["roles"].copy()
    if roles[seat] != role:
        other = roles.index(role)
        roles[seat], roles[other] = roles[other], roles[seat]
    table = Table({**record["setup"], "roles": roles}, Random(0))
    table.started = True
    for event in record["events"][:index]:
        table.commit(event)
    return {
        "seat": seat,
        "state": table.game.view(seat),
        "choices": table.choices(seat, 0),
        "history": table.history[seat],
    }


def positions(folder):
    for seed in (22, 23, 31, 32, 33):
        record = read(folder / f"reference-{seed}" / "game.json")
        for index, event in enumerate(record["events"]):
            if event["kind"] != "place":
                continue
            good = snapshot_at(record, index, "good")
            if seed in (22, 23) and good["state"]["turn"] != 2:
                continue
            pair = menu(good["state"], good["choices"])
            if pair:
                yield seed, index + 1, pair, good, snapshot_at(record, index, "bad")
                break


def decide(model, snapshot, actions, literal):
    body = model_request(snapshot, model)
    context = json.loads(body["messages"][1]["content"])
    options = []
    for action in actions:
        face, r = action["tile"], action["rotation"]
        options.append({"id": f"face{face}-r{r}", **action, "oriented": tile(rotate(face, r))})
    context["options"] = options
    values = [o["id"] for o in options] if literal else list(range(len(options)))
    body["messages"][0]["content"] = (
        RULES
        + " "
        + (
            "Consider these two complete legal placements. Assume the marker enters the chosen tile. "
            "Good wants to keep a route to EXIT open. Bad wants to permanently cut off EXIT. "
            + (
                "Return the chosen id"
                if literal
                else "Return the ZERO-BASED INDEX of the chosen placement"
            )
            + " as build."
        )
    )
    body["messages"][1]["content"] = json.dumps(context, separators=(",", ":"))
    body["format"] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["build"],
        "properties": {"build": {"type": "string" if literal else "integer", "enum": values}},
    }
    body["think"] = False
    reply = json.loads(request(11434, "/api/chat", body, 15)["message"]["content"])
    result = reply["build"]
    if type(result) is not type(values[0]):
        raise ValueError(f"invalid build response {reply!r}")
    return values.index(result)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("folder", type=Path)
    cli.add_argument("--models", nargs="+", default=["llama3.1:8b", "qwen3.5:4b"])
    args = cli.parse_args()
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(
        ["seed", "event", "seat", "role", "model", "encoding", "first", "trap", "onward", "chosen"]
    )
    for seed, event, pair, good, bad in positions(args.folder):
        for snap in (good, bad):
            for model in args.models:
                for first, second in (("trap", "onward"), ("onward", "trap")):
                    labels = [first, second]
                    for literal in (False, True):
                        i = decide(model, snap, [pair[k] for k in labels], literal)
                        writer.writerow(
                            [
                                seed,
                                event,
                                snap["seat"],
                                snap["state"]["role"],
                                model,
                                "literal" if literal else "index",
                                first,
                                *(
                                    json.dumps(pair[k], separators=(",", ":"))
                                    for k in ("trap", "onward")
                                ),
                                labels[i],
                            ]
                        )
                        sys.stdout.flush()
