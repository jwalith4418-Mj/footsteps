"""Compare identical private-seat requests across window sizes with empty and warm KV caches."""

import argparse
import hashlib
import json
from pathlib import Path
from time import monotonic

from experiments.persistent_proposals import prepared
from experiments.persistent_runtime import resident_model
from footsteps.ollama import ServiceError, request
from footsteps.session import CONTEXT_WINDOWS


def frozen_request(model, reads):
    session, _ = prepared("east")
    body = None

    def read_state(_port, _path, request_body, _budget):
        nonlocal body
        body = request_body
        return {"message": {"tool_calls": [{"function": {"name": "get_state", "arguments": {}}}]}}

    # Each read observes the same legal bridge, with the referee clock fixed.
    for _ in range(reads + 1):
        session.step(model, infer=read_state)
    return body


def measure(output, model, contexts, reads):
    with output.open("x") as f:
        for ctx in contexts:
            for n in reads:
                body = frozen_request(model, n)
                digest = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
                body["options"]["num_ctx"] = ctx
                # This standalone experiment owns the model during the block. Unload between
                # cases so a shorter conversation cannot share a long prefix with the next one.
                for keep in ("0", "10m"):
                    request(
                        11434,
                        "/api/chat",
                        {
                            "model": model,
                            "messages": [],
                            "stream": False,
                            "keep_alive": keep,
                            "options": {"num_ctx": ctx},
                        },
                        120,
                    )
                resident = resident_model(model)
                for cache in ("empty", "repeat"):
                    start = monotonic()
                    row = {
                        "model": model,
                        "num_ctx": ctx,
                        "reads": n,
                        "cache": cache,
                        "input_sha256_before_context_change": digest,
                        "resident": resident,
                    }
                    try:
                        reply = request(11434, "/api/chat", body, 120)
                    except ServiceError as exc:
                        row.update(status=exc.status, seconds=round(monotonic() - start, 4))
                        print(json.dumps(row), file=f, flush=True)
                        continue
                    elapsed = monotonic() - start
                    calls = reply.get("message", {}).get("tool_calls", [])
                    row.update(
                        {
                            "status": 200,
                            "prompt_tokens": reply.get("prompt_eval_count"),
                            "reply_tokens": reply.get("eval_count"),
                            "done_reason": reply.get("done_reason"),
                            "tools": [c["function"]["name"] for c in calls],
                            "prefill_seconds": round(reply["prompt_eval_duration"] / 1e9, 4),
                            "generation_seconds": round(reply["eval_duration"] / 1e9, 4),
                            "seconds": round(elapsed, 4),
                        }
                    )
                    print(json.dumps(row), file=f, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--model", default="qwen3.5:9b-q8_0")
    parser.add_argument("--contexts", type=int, nargs="+", choices=CONTEXT_WINDOWS, required=True)
    parser.add_argument("--reads", type=int, nargs="+", default=[5])
    args = parser.parse_args()
    if min(args.reads) < 0:
        parser.error("reads must be nonnegative")
    measure(args.output, args.model, args.contexts, args.reads)
