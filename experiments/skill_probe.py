"""Frozen movement decisions from genuine stalls plus tight mirrored tactical positions."""

import argparse
import csv
import json
import sys
from pathlib import Path
from random import Random

from experiments.model_solitaire import decide, detour_table, geometry, label
from footsteps.board import distance, neighbors, optimistic_length
from footsteps.ollama import request
from footsteps.record import read
from footsteps.solo import sealed
from footsteps.table import Table

MODEL = "qwen3.5:9b-q8_0"
DATA = Path(__file__).with_name("model-solitaire")
SYSTEM = """You are the only player. Move the shared marker toward EXIT before the last movement opportunity.
This turn's build is over. Pick a movement action. EVERY choice, including wait, spends the current opportunity.
Entering EXIT wins now. Entering a closed region makes EXIT permanently unreachable. Use a detour when
the nearer landing is a trap. A future build can extend an open edge. Select the action by name."""


def card_choice(state, choices, model, bound=False):
    report = geometry(state, choices)["landings"]
    directions = dict(
        zip(neighbors(state["marker"]), ("north", "east", "south", "west"), strict=True)
    )
    names = ["wait" if p is None else directions[tuple(p)] for p in choices["to"]]
    rows = []
    for name, dest in zip(names, choices["to"], strict=True):
        landing = report[label(dest)]
        rows.append(
            {
                "action": name,
                "at": dest if dest is not None else state["marker"],
                "distance": landing["distance"],
                "closed_forever": landing["permanently_trapped"],
                "arrives_at_EXIT": landing["at_EXIT"],
                "onward_edges": landing["onward"],
            }
        )
    context = {
        "EXIT": state["goal"],
        "marker": state["marker"],
        "moves_including_now": state["store_count"] + 1,
        "edges": "direction:floor/unbuilt/EXIT:distance from next square to EXIT",
        "actions": rows,
    }
    system = SYSTEM
    if bound:
        board = {tuple(p): f for p, f in state["board"]}
        remaining = state["store_count"]
        lines = []
        for row in rows:
            length = optimistic_length(board, tuple(row["at"]), tuple(state["goal"]), remaining)
            if row["arrives_at_EXIT"]:
                outcome = "WIN IMMEDIATELY."
            elif row["closed_forever"]:
                outcome = "CERTAIN LOSS: there is no way out to EXIT."
            elif length is None:
                outcome = f"CERTAIN LOSS: even perfect future tiles cannot reach EXIT in the {remaining} steps left."
            else:
                outcome = f"Still possible. With perfect future tiles EXIT needs {length} more steps; {remaining} remain."
            lines.append(
                f"{row['action']}: {outcome} Landing is {row['distance']} squares from EXIT."
            )
        context = {"available_actions": lines}
        system = (
            "You control one move in Footsteps solitaire. You want to win. A pathfinding tool checked each"
            " legal move on an optimistic floor. Select a possible win over a certain loss. Prefer fewer steps"
            " to EXIT when several wins are possible. If all moves lose, approach EXIT. Reply with the action name."
        )
    body = {
        "model": model,
        "stream": False,
        "think": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": json.dumps(context, separators=(",", ":"))},
        ],
        "format": {
            "type": "object",
            "required": ["action"],
            "additionalProperties": False,
            "properties": {"action": {"type": "string", "enum": names}},
        },
        "options": {"temperature": 0, "seed": 1, "num_ctx": 8192, "num_predict": 96},
    }
    answer = json.loads(request(11434, "/api/chat", body, 30)["message"]["content"])
    return {"to": choices["to"][names.index(answer["action"])]}


def positions():
    found = 0
    for path in sorted((DATA / "test-edges").glob("game-*.json")):
        record = read(path)
        table = Table(record["setup"], Random(0))
        table.started = True
        for n, event in enumerate(record["events"], 1):
            if event["kind"] == "propose" and event["to"] is None:
                state = table.game.view(0)
                opts = table.choices(0, 0)
                goal, marker = table.game.goal, table.game.marker
                targets = [
                    p
                    for p in opts["to"]
                    if p is not None
                    and distance(p, goal) < distance(marker, goal)
                    and not sealed(table.game.board, p, goal)
                ]
                if targets:
                    yield f"{path.stem}-e{n}", "recorded", state, opts, set(targets)
                    found += 1
                    break
            table.commit(event)
        if found == 4:
            break
    for sx in (-1, 1):
        for sy in (-1, 1):
            table = detour_table(sx, sy, 5)
            state = table.game.view(0)
            state["moves_left_including_current"] = 4
            yield f"{sx},{sy}", "tight", state, {"to": [None, (sx, 0), (0, sy)]}, {(0, sy)}


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument(
        "--policy", choices=["original", "card", "bound"], nargs="+", default=["original", "card"]
    )
    args = cli.parse_args()
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(
        ["case", "kind", "model", "policy", "reverse", "options", "choice", "qualifies"]
    )
    for case, kind, state, choices, targets in positions():
        for reverse in (False, True):
            opts = {"to": choices["to"][::-1] if reverse else choices["to"]}
            for policy in args.policy:
                action = (
                    card_choice(state, opts, args.model, bound=policy == "bound")
                    if policy != "original"
                    else decide(state, opts, args.model, aided=True)
                )
                dest = action["to"]
                writer.writerow(
                    [
                        case,
                        kind,
                        args.model,
                        policy,
                        reverse,
                        " ".join(map(label, opts["to"])),
                        label(dest),
                        dest in targets,
                    ]
                )
                sys.stdout.flush()
