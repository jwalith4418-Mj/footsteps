"""Compare printed orientation, unaided rotation, shown rotations and optional lookup."""

import argparse
import csv
import json
from itertools import product
from pathlib import Path
from random import Random
from time import monotonic

from experiments.action_probe import GUEST, ROOT, position
from experiments.skill_probe import MODEL
from footsteps.board import STEPS, moves, optimistic_length, rotate
from footsteps.ollama import consultation, decode_choice, model_request, request
from footsteps.seat_tools import tile
from footsteps.solo import sealed
from footsteps.table import Table
from footsteps.team_names import color_brief

ARMS = ("ordinary", "fixed", "table", "tool")


def single_face(face, goal, at):
    table = Table({"hands": [[]], "store": [face] * 4, "goal": goal, "roles": ["good"]}, Random(0))
    table.join(0, 0)
    snap = table.view(0, 0)
    snap["choices"]["at"] = [at]
    return snap


def cases():
    for face, turns in product((40, 33), range(4)):
        _, entry, outward = tile(rotate(face, turns))
        dx, dy = STEPS["NESW".index(entry)]
        at = (-dx, -dy)
        dx, dy = STEPS["NESW".index(outward)]
        goal = [at[0] + dx, at[1] + dy]
        snap = single_face(face, goal, at)
        task = f"Place your tile at the specified square with an entrance on {entry} and exit on {outward}."
        yield f"ports-{face}-{turns}", snap, task, turns
    yield "Blue-8602", position(ROOT / "exit-origin/social/8602-bad1+3.json", 41, 4), "", None
    yield "Red-guest", position(GUEST, 23, 2), "", None
    for seed, red in product((8101, 8102), (1, 2)):
        yield (
            f"transfer-{seed}-R{red}",
            position(ROOT / f"social/fresh-base/{seed}-bad{red}.json", 10, 2),
            "",
            None,
        )


def success(state, tile_id, rotation, at, target):
    if target is not None:
        return rotation == target
    board = dict(state["board"])
    board[at] = rotate(tile_id, rotation)
    marker, goal = state["marker"], state["goal"]
    if state["role"] == "bad":
        return sealed(board, marker, goal)
    # All social prefixes used here drew two and will return one tile.
    return any(
        optimistic_length(board, p, goal, state["store_count"] + 1) is not None
        for p in moves(board, marker)
    )


def pick(snap, model, arm, task, reverse, named):
    options = {k: vs[::-1] if reverse else vs for k, vs in snap["choices"].items()}
    if arm == "fixed":
        options["rotation"] = [0]
    snap = {**snap, "choices": options}
    body = model_request(
        snap, model, show_rotations=arm == "table", explicit_actions=True, named_rotations=named
    )
    if snap.get("team_names") == "colors":
        color_brief(body)
    body["think"] = False
    ctx = json.loads(body["messages"][1]["content"])
    if task:
        ctx["task"] = task
    if arm == "fixed":
        ctx["placement_rule"] = (
            "Every tile stays in printed orientation. Choose only the face and square."
        )
        del ctx["options"]["rotation"]
        del body["format"]["properties"]["rotation"]
        body["format"]["required"].remove("rotation")
    body["messages"][1]["content"] = json.dumps(ctx, separators=(",", ":"))
    started = monotonic()
    used = []
    metrics = {}
    if arm == "tool":
        messages, used = consultation(
            snap, body, 15, board_tools=False, rotation_lookup=True, metrics=metrics
        )
        body["messages"].extend(messages)
    remaining = 30 - (monotonic() - started)
    status = "accepted"
    choice = {}
    try:
        if remaining <= 0:
            raise TimeoutError("decision deadline")
        answer = request(11434, "/api/chat", body, remaining)
        metrics["prompt_tokens"] = metrics.get("prompt_tokens", 0) + answer["prompt_eval_count"]
        metrics["output_tokens"] = metrics.get("output_tokens", 0) + answer["eval_count"]
        choice, _ = decode_choice(
            answer, body, {k: options[k] for k in body["format"]["required"]}, False
        )
        choice.setdefault("rotation", 0)
        if monotonic() - started >= 30:
            raise TimeoutError("decision deadline")
    except (OSError, ValueError, KeyError) as exc:
        status = type(exc).__name__
        choice = {}
    return choice, {
        "status": status,
        "lookup": used[0]["status"] if used else "",
        "requested_face": used[0].get("tile") if used else None,
        "seconds": round(monotonic() - started, 3),
        **metrics,
    }


def run(output, model, named):
    with output.open("x") as f:
        rows = None
        for i, (case, snap, task, target) in enumerate(cases()):
            for reverse in (False, True):
                for offset in range(len(ARMS)):
                    arm = ARMS[(i + int(reverse) + offset) % len(ARMS)]
                    if named and arm == "fixed":
                        continue
                    choice, info = pick(snap, model, arm, task, reverse, named)
                    opts = snap["choices"]
                    actions = list(
                        product(
                            opts["tile"], [0] if arm == "fixed" else opts["rotation"], opts["at"]
                        )
                    )
                    viable = sum(success(snap["state"], *a, target) for a in actions)
                    won = bool(choice) and success(
                        snap["state"], choice["tile"], choice["rotation"], choice["at"], target
                    )
                    row = {
                        "case": case,
                        "arm": arm,
                        "reverse": reverse,
                        "model": model,
                        "role": snap["state"]["role"],
                        "actions": len(actions),
                        "viable": viable,
                        "picked_face": choice.get("tile"),
                        "rotation": choice.get("rotation"),
                        "at": choice.get("at"),
                        "success": int(won),
                        "prompt_tokens": None,
                        "output_tokens": None,
                        **info,
                    }
                    if rows is None:
                        rows = csv.DictWriter(f, row, lineterminator="\n")
                        rows.writeheader()
                    rows.writerow(row)
                    f.flush()


def controls(output, model):
    """Check requests when every rotation of the offered tile gives exactly the same floor."""
    with output.open("x") as f:
        rows = None
        for face, explicit, reverse in product((0, 255), (False, True), (False, True)):
            snap = single_face(face, [2, 0], (1, 0))
            task = "Place the tile on the offered square."
            if explicit:
                task += " Every clockwise rotation of this face has exactly the same entrances and exits."
            choice, info = pick(snap, model, "tool", task, reverse, True)
            row = {
                "face": face,
                "invariance_stated": explicit,
                "reverse": reverse,
                "model": model,
                "rotation": choice.get("rotation"),
                "prompt_tokens": None,
                "output_tokens": None,
                **info,
            }
            if rows is None:
                rows = csv.DictWriter(f, row, lineterminator="\n")
                rows.writeheader()
            rows.writerow(row)
            f.flush()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument("--named-rotations", action="store_true")
    cli.add_argument(
        "--controls",
        action="store_true",
        help="offer the lookup on invariant tiles with named turns",
    )
    args = cli.parse_args()
    if args.controls:
        controls(args.output, args.model)
    else:
        run(args.output, args.model, args.named_rotations)
