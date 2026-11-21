"""A five-seat table with a seat-relative boolean removal ballot at every nomination."""

import argparse
from pathlib import Path

from experiments.goal_pursuit import run
from experiments.pivotal_votes import prompt
from footsteps.decision_notes import save_note
from footsteps.ollama import decode_choice, request


def removal(snap, model, notes, log):
    body = prompt(snap, model, "live-binary")
    body["options"]["num_predict"] = 320
    reply = request(11434, "/api/chat", body, 30)
    log.append({key: reply.get(key) for key in ("prompt_eval_count", "eval_count", "done_reason")})
    if reply.get("done_reason") == "length":
        raise ValueError("reply cap")
    choice, reason = decode_choice(reply, body, snap["choices"], True)
    save_note(notes, snap, model, choice, reason, [])
    return choice


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=Path)
    cli.add_argument("private", type=Path)
    cli.add_argument("--seed", type=int, default=9901)
    cli.add_argument("--model", required=True)
    args = cli.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    args.private.mkdir(parents=True, exist_ok=True)
    run(
        args.root,
        args.private,
        "five",
        args.seed,
        "clear",
        args.model,
        max_reply=320,
        removal_policy=removal,
    )
