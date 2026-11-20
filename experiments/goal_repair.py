"""Observe changes to a seat-authored first landing after checking only its own candidate."""

import argparse
import json
from pathlib import Path
from random import Random
from time import monotonic

from experiments.goal_pursuit import HEADINGS, budget, card, floor_report, worksheet
from experiments.plan_tactics import detour_table
from experiments.skill_probe import MODEL
from footsteps.board import rotate
from footsteps.game import with_exit_origin
from footsteps.ollama import request
from footsteps.table import Table


def inspect(snap, draft):
    state = snap["state"]
    marker, goal = tuple(state["marker"]), tuple(state["goal"])
    fields = ("tile", "rotation", "build_x", "build_y", "landing_x", "landing_y", "further_steps")
    if not isinstance(draft, dict) or not all(type(draft.get(k)) is int for k in fields):
        return {"error": "Supply all seven literal integers."}
    face, turns = draft["tile"], draft["rotation"]
    at = (draft["build_x"], draft["build_y"])
    if (
        face not in state["hand"]
        or turns not in range(4)
        or at not in map(tuple, snap["choices"]["at"])
    ):
        return {
            "error": "Use a held face, an absolute rotation 0–3 and an empty legal build square."
        }
    board = {tuple(p): f for p, f in state["board"]}
    board[at] = rotate(face, turns)
    after = budget(state)
    report = floor_report(board, marker, goal, after)
    landing = (draft["landing_x"], draft["landing_y"])
    viable = any(p == landing and n is not None for p, n, _ in report)
    return {
        "marker_after_build": marker,
        "actual_remaining_after_step": after,
        "landings": card(report),
        "proposed_step_legal": any(p == landing for p, _, _ in report),
        "possible_to_finish_from_proposed_landing": viable,
    }


def probe(table, model):
    snap = table.view(0, 0)
    s = snap["state"]
    fields = ("tile", "rotation", "build_x", "build_y", "landing_x", "landing_y", "further_steps")
    messages = [
        {
            "role": "system",
            "content": "You play Blue solitaire. Win by entering EXIT before movement opportunities run out. Plan one build then a legal step or stay. Supply your own literal plan and the number of steps remaining after this one. You may commit a legal build with any resulting prospects.",
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "worksheet": worksheet(snap),
                    "floor": s["board"],
                    "empty_build_squares": snap["choices"]["at"],
                }
            ),
        },
    ]
    body = {
        "model": model,
        "stream": False,
        "think": False,
        "messages": messages,
        "format": {
            "type": "object",
            "properties": {k: {"type": "integer"} for k in fields},
            "required": list(fields),
        },
        "options": {"num_ctx": 4096, "num_predict": 130, "temperature": 0, "seed": 1},
    }
    deadline = monotonic() + 30
    row = {"attempts": [], "committed": False, "viable": False}
    try:
        for attempt in range(2):
            left = deadline - monotonic()
            if left <= 0:
                raise TimeoutError("expired")
            response = request(11434, "/api/chat", body, left)["message"]["content"]
            if monotonic() >= deadline:
                raise TimeoutError("late")
            draft = json.loads(response)
            facts = inspect(snap, draft)
            row["attempts"].append({"draft": draft, "check": facts})
            if attempt == 0:
                messages.extend(
                    [
                        {"role": "assistant", "content": response},
                        {
                            "role": "user",
                            "content": f"The check on YOUR candidate is {json.dumps(facts)}. Keep it or submit a revised final plan.",
                        },
                    ]
                )
        if "error" not in facts:
            table.submit(
                0,
                table.revision,
                {
                    "tile": draft["tile"],
                    "rotation": draft["rotation"],
                    "at": [draft["build_x"], draft["build_y"]],
                },
                0,
            )
            row.update(committed=True, viable=facts["possible_to_finish_from_proposed_landing"])
    except (OSError, ValueError) as exc:
        row["error"] = str(exc)
    return row


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--model", default=MODEL)
    args = p.parse_args()
    with args.output.open("x") as out:
        for heading, goal in HEADINGS.items():
            t = Table(
                with_exit_origin(
                    {"roles": ["good"], "hands": [[65]], "store": [65, 65], "goal": goal}
                ),
                Random(0),
            )
            t.join(0, 0)
            out.write(
                json.dumps({"case": heading, **probe(t, args.model)}, separators=(",", ":")) + "\n"
            )
            out.flush()
        for x, y in ((1, 1), (-1, 1), (1, -1), (-1, -1)):
            out.write(
                json.dumps(
                    {"case": [x, y], **probe(detour_table(x, y), args.model)}, separators=(",", ":")
                )
                + "\n"
            )
            out.flush()
