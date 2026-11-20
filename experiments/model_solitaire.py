"""Single model, literal legal actions, referee-controlled chance and solitaire ballots."""

import argparse
import csv
import json
import time
from http.client import HTTPException
from pathlib import Path
from random import Random

from experiments.seat_chart import seat_chart
from footsteps.board import connects, distance, neighbors, rotate
from footsteps.fallback import timeout
from footsteps.ollama import request, tile
from footsteps.record import replay
from footsteps.solo import sealed, setup, simulate
from footsteps.table import Table

MODEL = "qwen2.5:32b"
RULES = """You alone control the marker in Footsteps solitaire. Reach EXIT before time runs out.
Each turn place a tile, discard a tile if asked, then optionally move one square.
A move needs an exit on the current tile and an entrance on the facing side of the destination.
Unbuilt squares need a tile before entry. Existing tiles cannot be replaced. The EXIT is already placed.
North is +y, east is +x. Tiles are [face, entrances, exits] in NESW compass directions.
Rotation 1 turns both sets 90 degrees clockwise, 2 turns 180 degrees, 3 turns 270 degrees.
Keep a usable route onward as you approach EXIT. Enter EXIT as soon as possible.
Return literal values from the legal menu for this stage. Coordinates are strings x,y."""


def label(point):
    return "stay" if point is None else f"{point[0]},{point[1]}"


def local_edges(board, pos, face, goal):
    """List usable outgoing directions, including opportunities into unbuilt squares."""
    result = []
    for direction, dest in enumerate(neighbors(pos)):
        if not face & (16 << direction):
            continue
        if dest in board and not connects(face, board[dest], direction):
            continue
        kind = "EXIT" if dest == goal else ("floor" if dest in board else "unbuilt")
        result.append(f"{'NESW'[direction]}:{kind}:{distance(dest, goal)}")
    return result


def geometry(state, choices):
    board = {tuple(p): f for p, f in state["board"]}
    marker, goal = tuple(state["marker"]), tuple(state["goal"])
    if "to" in choices:
        report = {}
        for step in choices["to"]:
            dest = marker if step is None else tuple(step)
            report[label(step)] = {
                "distance": distance(dest, goal),
                "at_EXIT": dest == goal,
                "permanently_trapped": sealed(board, dest, goal),
                "onward": local_edges(board, dest, board[dest], goal),
            }
        return {"landings": report}
    if "at" not in choices:
        return {}
    entries = []
    squares = set(map(tuple, choices["at"]))
    for direction, pos in enumerate(neighbors(marker)):
        if pos not in squares:
            continue
        builds = []
        for face in choices["tile"]:
            for r in choices["rotation"]:
                oriented = rotate(face, r)
                if connects(board[marker], oriented, direction):
                    builds.append([face, r, local_edges(board, pos, oriented, goal)])
        if builds:
            entries.append(
                {"at": label(pos), "distance": distance(pos, goal), "enterable_builds": builds}
            )
    return {"placements_next_to_marker": entries}


def payload(state, choices, model, aided=False, chart=False):
    options = {
        k: [label(p) for p in values] if k in ("at", "to") else values
        for k, values in choices.items()
    }
    context = {k: state[k] for k in ("goal", "marker", "turn", "stage", "store_count")}
    if "moves_left_including_current" in state:
        context["moves_left_including_current"] = state["moves_left_including_current"]
    context.update(
        hand=[tile(f) for f in state["hand"]],
        board=[[pos, tile(f)] for pos, f in state["board"]],
        options=options,
    )
    system = RULES
    if aided:
        context.update(geometry(state, choices))
        system += (
            " The geometry report lists each enterable local build as [face,rotation,onward edges]."
            " Each edge is direction:kind:Manhattan distance to EXIT after one further step."
            " Unbuilt needs a future placement. All original legal choices remain available."
            " At a move, inspect permanent traps and the distance remaining."
        )
    if chart:
        del context["board"], context["hand"]
    content = json.dumps(context, separators=(",", ":"))
    if chart:
        content += "\n\n" + seat_chart(state)
    schema = {
        k: {"type": "string" if k in ("at", "to") else "integer", "enum": v}
        for k, v in options.items()
    }
    return {
        "model": model,
        "stream": False,
        "think": False,
        "format": {
            "type": "object",
            "properties": schema,
            "required": list(options),
            "additionalProperties": False,
        },
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": content},
        ],
        "options": {"temperature": 0, "seed": 1, "num_ctx": 8192, "num_predict": 96},
    }


def decide(
    state,
    choices,
    model,
    aided=False,
    think=False,
    metrics=None,
    *,
    chart=False,
):
    body = payload(state, choices, model, aided, chart)
    if think:
        body["think"] = True
        body["options"]["num_predict"] = 1024
    deadline_seconds = 60 if think else 30
    started = time.monotonic()
    answer = request(11434, "/api/chat", body, deadline_seconds)
    if metrics is not None:
        metrics.update(
            tokens=answer.get("eval_count"),
            thinking_returned=bool(answer["message"].get("thinking")),
            stop_reason=answer.get("done_reason"),
        )
    if time.monotonic() - started > deadline_seconds:
        raise TimeoutError("decision arrived after the deadline")
    try:
        reply = json.loads(answer["message"]["content"])
    except json.JSONDecodeError as exc:
        if answer.get("done_reason") == "length":
            raise ValueError("token limit reached without a complete action") from exc
        raise
    if not isinstance(reply, dict) or reply.keys() != choices.keys():
        raise ValueError("invalid decision fields")
    decoded = {}
    for k, values in choices.items():
        allowed = body["format"]["properties"][k]["enum"]
        if type(reply[k]) is not type(allowed[0]):
            raise ValueError("wrong literal type")
        decoded[k] = values[allowed.index(reply[k])]
    return decoded


def run_game(seed, model, out, aided=False, think=False, chart=False):
    initial = setup(seed, (4, 2), 2, 10, 0.55)
    table = Table(initial, Random(f"draw/{seed}"), discussion=0)
    rng = Random(f"fallback/{seed}")
    table.join(0, 0)
    calls = []
    while not table.game.winner:
        state = table.game.view(0)
        stage = state["stage"]
        if stage == "move_vote":
            table.commit({"kind": stage, "votes": [True]})
        else:
            start = time.monotonic()
            error = ""
            metrics = dict.fromkeys(("tokens", "thinking_returned", "stop_reason")) if think else {}
            try:
                choice = decide(
                    state,
                    table.choices(0, 0),
                    model,
                    aided,
                    think,
                    metrics if think else None,
                    chart=chart,
                )
                event = {"kind": stage, **choice}
            except (OSError, HTTPException, ValueError, KeyError) as exc:
                error = f"{type(exc).__name__}: {exc}"
                event = timeout(table.game, rng)
            calls.append(
                {
                    "event": table.revision + 1,
                    "stage": stage,
                    "ms": round(1000 * (time.monotonic() - start)),
                    "error": error,
                    **metrics,
                }
            )
            table.commit(event)
        table.open_decision(0)
    g = replay(table.record)
    (out / f"game-{seed}.json").write_text(json.dumps(table.record, indent=2) + "\n")
    with (out / f"calls-{seed}.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=calls[0], lineterminator="\n")
        w.writeheader()
        w.writerows(calls)
    result = [
        seed,
        model,
        int(g.winner == "good"),
        g.turn,
        distance(g.marker, g.goal),
        int(sealed(g.board, g.marker, g.goal)),
        sum(bool(r["error"]) for r in calls),
    ]
    rows = [result]
    for policy in ("random", "greedy", "exits", "route"):
        r, _ = simulate(initial, seed, policy)
        rows.append([seed, policy, r["win"], r["turns"], r["end_distance"], r["sealed"], 0])
    return rows


def detour_table(sx, sy, store):
    # Reflect the eastern trap (W entrance) and northern detour (S entrance, E exit).
    trap = 8 if sx == 1 else 2
    detour = (4 if sy == 1 else 1) | (32 if sx == 1 else 128)
    goal = [2 * sx, 0]
    table = Table(
        {"goal": goal, "roles": ["good"], "hands": [[trap, detour]], "store": [255] * store},
        Random(0),
    )
    for pos, face in [([sx, 0], trap), ([0, sy], detour)]:
        table.commit({"kind": "draw", "tiles": [255, 255]})
        table.commit({"kind": "place", "at": pos, "tile": face, "rotation": 0})
        table.commit({"kind": "discard", "tile": 255})
        if face == trap:
            table.commit({"kind": "propose", "to": None})
    table.started = True
    return table


def detours(model, aided=False, think=False, tight=False, chart=False):
    for sx in (1, -1):
        for sy in (1, -1):
            table = detour_table(sx, sy, 5 if tight else 10)
            state = table.game.view(0)
            if tight:
                state["moves_left_including_current"] = state["store_count"] + 1
            choices = table.choices(0, 0)
            assert set(map(label, choices["to"])) == {"stay", label([sx, 0]), label([0, sy])}
            for reverse in (False, True):
                steps = [(sx, 0), (0, sy)]
                if reverse:
                    steps.reverse()
                try:
                    move = decide(state, {"to": [None, *steps]}, model, aided, think, chart=chart)[
                        "to"
                    ]
                    yield [sx, sy, reverse, label(move), move == (0, sy)]
                except (OSError, HTTPException, ValueError, KeyError) as exc:
                    yield [sx, sy, reverse, f"{type(exc).__name__}: {exc}", False]


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument("--seeds", type=int, nargs="+", required=True)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--detours", action="store_true")
    cli.add_argument("--tight-detours", action="store_true")
    cli.add_argument("--ascii", action="store_true", help="append a north-up board and hand chart")
    cli.add_argument("--aided", action="store_true")
    cli.add_argument(
        "--think", action="store_true", help="use a 60-second clock and up to 1024 generated tokens"
    )
    args = cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    # Model loading gets its own clock, separate from a player decision.
    request(
        11434,
        "/api/generate",
        {"model": args.model, "stream": False, "options": {"num_ctx": 8192}},
        180,
    )
    for filename, enabled, tight in [
        ("detours.csv", args.detours, False),
        ("tight-detours.csv", args.tight_detours, True),
    ]:
        if enabled:
            with (args.out / filename).open("w") as f:
                w = csv.writer(f, lineterminator="\n")
                w.writerow(["sx", "sy", "reversed", "move", "correct"])
                w.writerows(detours(args.model, args.aided, args.think, tight, args.ascii))
    with (args.out / "results.csv").open("w") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["seed", "player", "win", "turns", "end_distance", "sealed", "fallback"])
        for seed in args.seeds:
            rows = run_game(seed, args.model, args.out, args.aided, args.think, args.ascii)
            w.writerows(rows)
            f.flush()
            print(rows[0], flush=True)
    loaded = request(11434, "/api/ps", None, 3)
    (args.out / "residency.json").write_text(
        json.dumps(
            [
                {k: m[k] for k in ("name", "size", "size_vram", "context_length")}
                for m in loaded["models"]
            ],
            indent=2,
        )
        + "\n"
    )
