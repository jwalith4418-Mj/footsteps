"""Matched games with one movement policy and the same model builder and discarder."""

import argparse
import csv
from pathlib import Path
from random import Random

from experiments.model_solitaire import decide, run_game
from experiments.skill_probe import MODEL, card_choice, optimistic_length
from footsteps.board import distance
from footsteps.ollama import request


def selector(policy, rng):
    def choose(state, choices, model, *args, **kwargs):
        if state["stage"] != "propose":
            return decide(state, choices, model, *args, **kwargs)
        if policy == "model":
            return card_choice(state, choices, model, bound=True)
        options = choices["to"]
        if policy == "uniform":
            return {"to": rng.choice(options)}
        board = {tuple(p): face for p, face in state["board"]}
        goal = tuple(state["goal"])

        def score(dest):
            pos = tuple(state["marker"] if dest is None else dest)
            length = optimistic_length(board, pos, goal, state["store_count"])
            return (length is None, length if length is not None else distance(pos, goal))

        best = min(map(score, options))
        return {"to": rng.choice([p for p in options if score(p) == best])}

    return choose


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument("--policy", choices=["model", "uniform", "shortest"], required=True)
    cli.add_argument("--seeds", type=int, nargs="+", required=True)
    cli.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    request(
        11434,
        "/api/generate",
        {"model": args.model, "stream": False, "options": {"num_ctx": 8192}},
        180,
    )
    with (args.out / "results.csv").open("w") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["seed", "player", "win", "turns", "end_distance", "sealed", "fallback"])
        for seed in args.seeds:
            choose = selector(args.policy, Random(f"movement/{seed}"))
            rows = run_game(seed, args.model, args.out, aided=True, decide_fn=choose)
            rows[0][1] = f"{args.model}/{args.policy}-movement"
            writer.writerows(rows)
            handle.flush()
            print(rows[0], flush=True)
