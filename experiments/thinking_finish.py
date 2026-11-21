"""Give a capped RANA ballot one commit-only call, with or without its own saved draft."""

import argparse
import hashlib
import json
from pathlib import Path
from time import monotonic

from experiments.ballot_thinking import MODELS, position
from footsteps.decision_notes import open_private
from footsteps.ollama import request


def finish(case, team, model, draft):
    _, s = position(case, team)
    tokens = 0
    thinking = ""

    def commit(port, path, body, timeout):
        nonlocal tokens, thinking
        messages = list(body["messages"])
        if draft is not None:
            messages.append({"role": "assistant", "content": draft})
        messages.append(
            {"role": "user", "content": "Cast your movement ballot now using vote_move."}
        )
        body = body | {
            "messages": messages,
            "think": False,
            "tools": [t for t in body["tools"] if t["function"]["name"] == "vote_move"],
        }
        reply = request(port, path, body, timeout)
        tokens = reply["eval_count"]
        thinking = reply["message"].get("thinking", "")
        return reply

    start = monotonic()
    s.step(model, infer=commit, budget=90)
    return s.seat.table.votes.get(s.snap["seat"]), tokens, round(monotonic() - start, 3), thinking


def run(receipts, private, out, sidecar):
    data = [json.loads(line) for line in receipts.read_text().splitlines()]
    owner = [json.loads(line) for line in private.read_text().splitlines()]
    with out.open("x") as public, open_private(sidecar) as secret:
        for row in data:
            if row["budget"] != 1536 or row["model"] != MODELS["27b"]:
                continue
            calls = row["calls"]
            if row["vote"] is not None or len(calls) != 1 or calls[0]["done_reason"] != "length":
                continue
            key = {k: row[k] for k in ("model", "case", "team", "seat", "budget", "revision")}
            (item,) = [
                r for r in owner if all(r[k] == v for k, v in key.items()) and r["index"] == 0
            ]
            text = item["thinking"]
            digest = hashlib.sha256(text.encode()).hexdigest()
            if digest != calls[0]["thinking_sha256"]:
                raise ValueError("capped draft digest does not match")
            for use in (False, True):
                vote, tokens, seconds, thinking = finish(
                    row["case"], row["team"], row["model"], text if use else None
                )
                result = key | {
                    "source_sha256": digest,
                    "with_draft": use,
                    "vote": vote,
                    "tokens": tokens,
                    "seconds": seconds,
                    "thinking_chars": len(thinking),
                    "thinking_sha256": hashlib.sha256(thinking.encode()).hexdigest()
                    if thinking
                    else None,
                }
                print(json.dumps(result), file=public, flush=True)
                print(json.dumps(result | {"thinking": thinking}), file=secret, flush=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("receipts", "private", "output", "sidecar"):
        cli.add_argument(name, type=Path)
    args = cli.parse_args()
    run(args.receipts, args.private, args.output, args.sidecar)
