"""Select one public build-and-walk plan per solitaire turn. The referee still checks each action."""

import argparse
import csv
import json
from pathlib import Path
from random import Random

from experiments.model_solitaire import label, local_edges, run_game
from experiments.skill_probe import MODEL, optimistic_length
from footsteps.board import distance, moves, neighbors, rotate
from footsteps.ollama import request
from footsteps.solo import sealed


def plans(state, choices, *, local=False):
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
                    if local:
                        edges = local_edges(board, landing, board[landing], goal)
                        key = dest, tuple(edges)
                        facts = {"edges": edges}
                    else:
                        length = optimistic_length(board, landing, goal, remaining)
                        trapped = length is None and sealed(board, landing, goal)
                        key = dest, length, trapped
                        facts = {"steps": length, "trapped": trapped}
                    if key not in unique:
                        unique[key] = {
                            "place": {"at": list(at), "tile": face, "rotation": r},
                            "to": dest,
                            **facts,
                            "distance": distance(landing, goal),
                        }
        del board[at]
    return list(unique.values())


def score(plan):
    if plan["steps"] is not None:
        return 0, plan["steps"], plan["distance"]
    return 1, plan["trapped"], plan["distance"]


def immediate_score(plan):
    onward = [int(edge.rsplit(":", 1)[1]) for edge in plan["edges"]]
    return (plan["distance"] != 0, not onward, plan["distance"], min(onward, default=999))


def select(menu, state, model, policy, rng, *, local=False):
    if policy == "uniform":
        return rng.choice(menu)
    if policy in ("shortest", "exits"):
        evaluate = immediate_score if local else score
        best = min(map(evaluate, menu))
        return rng.choice([p for p in menu if evaluate(p) == best])
    dirs = dict(zip(neighbors(state["marker"]), ("north", "east", "south", "west"), strict=True))
    choices = {}
    lines = []
    for p in menu:
        act = "wait" if p["to"] is None else dirs[tuple(p["to"])]
        key = f"{act}-{len(choices) + 1}"
        choices[key] = p
        if local:
            outcome = "Outgoing edges at landing: " + (", ".join(p["edges"]) or "none") + "."
            if p["distance"] == 0:
                outcome = "Arrive at EXIT."
        elif p["steps"] == 0:
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
    strategy = (
        "Select a legal turn plan to reach EXIT. A tool checked each plan on an optimistic floor. "
        "Prefer a possible win to a certain loss. Among possible wins prefer fewer remaining moves to EXIT. Return the plan name."
    )
    if local:
        strategy = (
            "You play Footsteps solitaire. Select a build and a move. Enter EXIT whenever possible. "
            "Make progress while keeping an onward exit. A tile with no outgoing edges strands the marker. "
            "Take a detour to avoid a dead end. Waiting costs a turn. Edges show direction:floor/unbuilt/EXIT:"
            "distance after the following step. An unbuilt square needs a tile first. Return the plan name."
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
                "content": strategy,
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


def policy_for(model, policy, seed, log, *, local=False):
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
        menu = plans(state, choices, local=local)
        order.shuffle(menu)
        chosen = select(menu, state, model, policy, picks, local=local)
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
    cli.add_argument("--policy", choices=["model", "uniform", "shortest", "exits"], required=True)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--seeds", type=int, nargs="+", required=True)
    cli.add_argument(
        "--local", action="store_true", help="group and display plans using only one-step edges"
    )
    args = cli.parse_args()
    if (args.local and args.policy == "shortest") or (not args.local and args.policy == "exits"):
        cli.error("use exits for local plans or shortest for pathfinding plans")
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
                choose = policy_for(args.model, args.policy, seed, log, local=args.local)
                rows = run_game(seed, args.model, args.out, decide_fn=choose)
            rows[0][1] = f"{args.policy}-local-plans" if args.local else f"{args.policy}-plans"
            w.writerows(rows)
            handle.flush()
            print(rows[0], flush=True)
