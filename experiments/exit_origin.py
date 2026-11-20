"""Compare coordinate origins on the same private solitaire observations and legal menus."""

import argparse
import csv
import json
from pathlib import Path
from random import Random

from experiments.model_solitaire import decide, label, run_game
from experiments.skill_probe import MODEL, positions
from footsteps.board import distance
from footsteps.ollama import request


def perspective(state, choices, origin):
    """Construct just the fields consumed by the solitaire adapter. Coordinates translate only."""
    ox, oy = state.get("start", (0, 0)) if origin == "start" else state["goal"]

    def shift(pos):
        return (pos[0] - ox, pos[1] - oy) if pos is not None else None

    view = {k: state[k] for k in ("turn", "stage", "store_count", "hand")}
    view.update(
        marker=shift(state["marker"]),
        goal=shift(state["goal"]),
        board=[(shift(pos), face) for pos, face in state["board"]],
    )
    if "moves_left_including_current" in state:
        view["moves_left_including_current"] = state["moves_left_including_current"]
    options = {k: [shift(v) for v in vs] if k in ("to", "at") else vs for k, vs in choices.items()}
    return view, options


def choose(origin, state, choices, model):
    view, options = perspective(state, choices, origin)
    choice = decide(view, options, model)
    # Decode through the unchanged order, so the referee receives its original literals.
    return {k: choices[k][options[k].index(value)] for k, value in choice.items()}


def games(out):
    out.mkdir(parents=True)
    with (out / "games.csv").open("x") as f:
        rows = csv.writer(f, lineterminator="\n")
        rows.writerow(
            ["origin", "seed", "model", "win", "turns", "end_distance", "sealed", "fallback"]
        )
        for seed in range(9101, 9105):
            for origin in ("start", "exit") if seed % 2 else ("exit", "start"):
                dest = out / origin
                dest.mkdir(exist_ok=True)

                result = run_game(seed, MODEL, dest, exit_origin=(origin == "exit"))[0]
                rows.writerow([origin, *result])
                f.flush()


def probes(out):
    with out.open("x") as f:
        rows = csv.writer(f, lineterminator="\n")
        rows.writerow(["case", "kind", "origin", "reversed", "eligible", "picked", "qualifies"])
        for case, kind, state, choices, targets in positions():
            for reverse in (False, True):
                opts = {"to": choices["to"][::-1] if reverse else choices["to"]}
                for origin in ("start", "exit"):
                    dest = choose(origin, state, opts, MODEL)["to"]
                    rows.writerow(
                        [
                            case,
                            kind,
                            origin,
                            reverse,
                            " ".join(sorted(map(label, targets))),
                            label(dest),
                            dest in targets,
                        ]
                    )
                    f.flush()


def distance_cases(confirm):
    if confirm:
        rng = Random(9110)
        # Four opening markers and eight positions elsewhere on the floor.
        for i in range(12):
            goal = (rng.choice((-1, 1)) * rng.randint(1, 6), rng.randint(-5, 5))
            marker = (0, 0) if i < 4 else (rng.randint(-6, 6), rng.randint(-6, 6))
            yield str(i), marker, goal
        return
    for i, (marker, goal) in enumerate(
        (
            ((0, -1), (2, 2)),  # Short social floor, turn five.
            ((-1, 1), (4, 2)),  # Long social floor, final marker.
            ((3, 4), (1, 2)),  # Past EXIT on both axes.
            ((-3, 2), (-3, 2)),  # Arrival.
        )
    ):
        for sign in (1, -1):
            yield (
                f"{i}-{'E' if sign == 1 else 'W'}",
                (sign * marker[0], marker[1]),
                (sign * goal[0], goal[1]),
            )


def bounds(out, confirm=False):
    with out.open("x") as f:
        rows = csv.writer(f, lineterminator="\n")
        rows.writerow(["case", "origin", "marker", "goal", "expected", "answer", "prompt_tokens"])
        for case, m, g in distance_cases(confirm):
            frames = {"start": (0, 0), "exit": g}
            if confirm:
                frames["marker"] = m
            for origin, (ox, oy) in frames.items():
                at = (m[0] - ox, m[1] - oy)
                target = (g[0] - ox, g[1] - oy)
                body = {
                    "model": MODEL,
                    "stream": False,
                    "think": False,
                    "messages": [
                        {
                            "role": "system",
                            "content": "A shared marker can take one north, east, south or west step per turn. Ignoring tiles and arrows, what is the fewest number of steps from marker to EXIT?",
                        },
                        {"role": "user", "content": json.dumps({"marker": at, "EXIT": target})},
                    ],
                    "format": {
                        "type": "object",
                        "properties": {"steps": {"type": "integer", "minimum": 0}},
                        "required": ["steps"],
                    },
                    "options": {
                        "temperature": 0,
                        "seed": 1,
                        "num_ctx": 8192,
                        "num_predict": 96,
                    },
                }
                reply = request(11434, "/api/chat", body, 30)
                value = json.loads(reply["message"]["content"])["steps"]
                rows.writerow(
                    [
                        case,
                        origin,
                        label(at),
                        label(target),
                        distance(m, g),
                        value,
                        reply["prompt_eval_count"],
                    ]
                )
                f.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task", choices=("games", "probes", "bounds", "bounds-check"))
    parser.add_argument("out", type=Path)
    args = parser.parse_args()
    if args.task.startswith("bounds"):
        bounds(args.out, confirm=args.task == "bounds-check")
    else:
        {"games": games, "probes": probes}[args.task](args.out)
