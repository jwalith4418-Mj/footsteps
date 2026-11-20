"""Select one public build-and-walk plan per solitaire turn. The referee still checks each action."""

import argparse
import csv
import json
from pathlib import Path
from random import Random

from experiments.model_solitaire import label, run_game
from experiments.skill_probe import MODEL, optimistic_length
from footsteps.board import distance, moves, neighbors, rotate
from footsteps.ollama import request
from footsteps.solo import sealed


def plans(state, choices):
    board = {tuple(p): f for p, f in state["board"]}
    goal, marker = tuple(state["goal"]), tuple(state["marker"])
    remaining = state["store_count"] + int(state["draw_count"] == 2)
    unique = {}
    for pos in choices["at"]:
        at = tuple(pos)
        for face in choices["tile"]:
            for r in choices["rotation"]:
                board[at] = rotate(face, r)
                for dest in [None, *moves(board, marker)]:
                    landing = marker if dest is None else dest
                    length = optimistic_length(board, landing, goal, remaining)
                    trapped = length is None and sealed(board, landing, goal)
                    key = dest, length, trapped
                    if key not in unique:
                        unique[key] = {
                            "place": {"at": list(at), "tile": face, "rotation": r},
                            "to": dest,
                            "steps": length,
                            "trapped": trapped,
                            "distance": distance(landing, goal),
                        }
        del board[at]
    return list(unique.values())


def score(plan):
    if plan["steps"] is not None:
        return 0, plan["steps"], plan["distance"]
    return 1, plan["trapped"], plan["distance"]


def select(menu, state, model, policy, rng):
    if policy == "uniform":
        return rng.choice(menu)
    if policy == "shortest":
        best = min(map(score, menu))
        return rng.choice([p for p in menu if score(p) == best])
    dirs = dict(zip(neighbors(state["marker"]), ("north", "east", "south", "west"), strict=True))
    choices = {}
    lines = []
    for p in menu:
        act = "wait" if p["to"] is None else dirs[tuple(p["to"])]
        key = f"{act}-{len(choices) + 1}"
        choices[key] = p
        if p["steps"] == 0:
            outcome = "Enter EXIT now: WIN."
        elif p["steps"] is not None:
            outcome = f"Possible win. With perfect tiles EXIT takes {p['steps']} further moves."
        elif p["trapped"]:
            outcome = "Certain loss: permanently trapped."
        else:
            outcome = "Certain loss: insufficient moves even with perfect future tiles."
        b = p["place"]
        lines.append(
            f"{key}: place face {b['tile']} rotation {b['rotation']} at {label(b['at'])}, "
            f"then {act}. {outcome} Ends {p['distance']} squares from EXIT."
        )
    body = {
        "model": model,
        "stream": False,
        "think": False,
        "format": {
            "type": "object",
            "required": ["plan"],
            "additionalProperties": False,
            "properties": {"plan": {"type": "string", "enum": list(choices)}},
        },
        "messages": [
            {
                "role": "system",
                "content": "Select a legal turn plan to reach EXIT. A tool checked each plan on an optimistic floor. Prefer a possible win to a certain loss. Among possible wins prefer fewer remaining moves to EXIT. Return the plan name.",
            },
            {
                "role": "user",
                "content": f"After this turn {state['store_count'] + int(state['draw_count'] == 2)} moves remain.\n"
                + "\n".join(lines),
            },
        ],
        "options": {"temperature": 0, "seed": 1, "num_ctx": 8192, "num_predict": 96},
    }
    reply = json.loads(request(11434, "/api/chat", body, 30)["message"]["content"])
    return choices[reply["plan"]]


def policy_for(model, policy, seed, log):
    order = Random(f"plan-order/{seed}")
    picks = Random(f"plan-pick/{seed}")
    chosen = None

    def decision(state, choices, _model, *args, **kwargs):
        nonlocal chosen
        if state["stage"] == "discard":
            return {"tile": min(choices["tile"], key=lambda f: (f.bit_count(), f))}
        if state["stage"] == "propose":
            if chosen is None:
                raise ValueError("no plan selected for this turn")
            dest = chosen["to"]
            chosen = None
            return {"to": dest}
        chosen = None
        menu = plans(state, choices)
        order.shuffle(menu)
        chosen = select(menu, state, model, policy, picks)
        log.write(
            json.dumps(
                {"turn": state["turn"], "menu": menu, "pick": menu.index(chosen)},
                separators=(",", ":"),
            )
            + "\n"
        )
        return chosen["place"]

    return decision


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument("--policy", choices=["model", "uniform", "shortest"], required=True)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--seeds", type=int, nargs="+", required=True)
    args = cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    if args.policy == "model":
        request(
            11434,
            "/api/generate",
            {"model": args.model, "stream": False, "options": {"num_ctx": 8192}},
            180,
        )
    with (args.out / "results.csv").open("w") as handle:
        w = csv.writer(handle, lineterminator="\n")
        w.writerow(["seed", "player", "win", "turns", "end_distance", "sealed", "fallback"])
        for seed in args.seeds:
            with (args.out / f"plans-{seed}.jsonl").open("w") as log:
                choose = policy_for(args.model, args.policy, seed, log)
                rows = run_game(seed, args.model, args.out, decide_fn=choose)
            rows[0][1] = f"{args.policy}-plans"
            w.writerows(rows)
            handle.flush()
            print(rows[0], flush=True)
