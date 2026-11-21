"""Measure a bounded native thinking budget on role-swapped social decisions."""

import argparse
import hashlib
import json
from pathlib import Path
from time import monotonic

from experiments.exit_interest import CONTEXT, MODELS, conditions, prefix, seat
from experiments.horizon_votes import fixture, seat_session
from experiments.persistent_runtime import resident_model
from footsteps.decision_notes import open_private
from footsteps.ollama import request
from footsteps.record import replay

CASES = ("13401", "trap")
TRANSFER = ("short", "detour")


def position(case, team):
    if case in TRANSFER:
        frozen = fixture(case, "west")
        session = seat_session(frozen, 3, team, context=CONTEXT)
        frozen["setup"]["roles"] = session.seat.table.game.roles.copy()
        return frozen, session
    frozen = prefix(case)
    builder = replay(frozen).actor
    ((voter, roles),) = [
        (v, r)
        for v, r in conditions(case)
        if v != builder and r[v] == team and r[builder] == "blue"
    ]
    frozen["setup"]["roles"] = roles
    return frozen, seat(case, voter, roles)


def run_vote(model, case, team, budget, owner):
    _, session = position(case, team)
    voter = session.snap["seat"]
    table = session.seat.table
    rev = table.revision
    key = {
        "model": model,
        "case": case,
        "seat": voter,
        "team": team,
        "turn": table.game.turn,
        "revision": rev,
        "budget": budget,
    }
    calls = []
    used = 0
    for index in range(5):
        remaining = budget - used
        if budget and remaining <= 0:
            break

        message = {}

        def infer(port, path, body, _timeout, remaining=remaining, index=index):
            nonlocal message
            body = dict(body, think=bool(budget))
            if budget:
                body["options"] = body["options"] | {"num_predict": remaining}
            start = monotonic()
            reply = request(port, path, body, max(90, remaining // 5))
            message = reply["message"]
            trace = message.get("thinking", "")
            receipt = {
                "index": index,
                "limit": body["options"]["num_predict"],
                "tokens": reply["eval_count"],
                "prompt_tokens": reply["prompt_eval_count"],
                "seconds": round(monotonic() - start, 3),
                "done_reason": reply.get("done_reason"),
                "thinking_chars": len(trace),
                "thinking_sha256": hashlib.sha256(trace.encode()).hexdigest() if trace else None,
            }
            print(
                json.dumps(
                    key
                    | receipt
                    | {
                        "thinking": trace,
                        "reply": message.get("content", ""),
                        "tool_calls": message.get("tool_calls", []),
                    }
                ),
                file=owner,
                flush=True,
            )
            calls.append(receipt)
            return reply

        row = session.step(model, infer=infer)
        if budget and len(session.messages) >= 2:
            assistant = session.messages[-2]
            if assistant["role"] == "assistant" and assistant.get("tool_calls") == message.get(
                "tool_calls"
            ):
                assistant["thinking"] = message.get("thinking", "")
                assistant["content"] = message.get("content", "")
        call = calls[-1]
        call["tool"] = row["tool"] if row and row.get("tool_offered") else None
        call["error"] = row is None or "error" in row["result"]
        used += call["tokens"]
        if voter in table.votes or table.revision != rev:
            break
    vote = table.votes.get(voter) if table.revision == rev else None
    return key | {
        "vote": vote,
        "aligned": vote is ((team == "blue") == (case in ("13401", "detour"))),
        "calls": calls,
    }


def run(model, budgets, output, private, cases=CASES):
    # Warm the exact context before attaching per-request wall times.
    request(
        11434,
        "/api/chat",
        {
            "model": model,
            "messages": [],
            "stream": False,
            "keep_alive": "10m",
            "options": {"num_ctx": CONTEXT},
        },
        120,
    )
    print(json.dumps(resident_model(model)))
    with output.open("x") as out, open_private(private) as owner:
        for budget in budgets:
            for case in cases:
                for team in ("red", "blue"):
                    row = run_vote(model, case, team, budget, owner)
                    print(json.dumps(row), file=out, flush=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("model", choices=MODELS)
    cli.add_argument("output", type=Path)
    cli.add_argument("private", type=Path)
    cli.add_argument(
        "--budgets",
        type=int,
        nargs="+",
        required=True,
        help="total generated tokens per thinking decision; 0 uses the ordinary no-thinking policy",
    )
    cli.add_argument("--cases", choices=CASES + TRANSFER, nargs="+", default=CASES)
    args = cli.parse_args()
    if len(set(args.budgets)) != len(args.budgets) or any(b < 0 or b > 8192 for b in args.budgets):
        cli.error("use unique budgets between 0 and 8192")
    run(MODELS[args.model], args.budgets, args.output, args.private, args.cases)
