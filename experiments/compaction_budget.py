"""Replay a private compact-only Ollama request at different output limits; log counts and status."""

import argparse
import hashlib
import json
import time
from pathlib import Path

from footsteps.ollama import INCOMPLETE_COMPACT, ServiceError, request


def measure(path, output, caps):
    body = json.loads(path.read_text())
    if [t["function"]["name"] for t in body["tools"]] != ["compact"]:
        raise ValueError("expected a frozen compact-only chat request")
    options = body["options"].copy()
    options.pop("num_predict", None)
    signature = hashlib.sha256(
        json.dumps(body | {"options": options}, sort_keys=True).encode()
    ).hexdigest()
    with output.open("x") as out:
        for cap in caps:
            body["options"]["num_predict"] = cap
            row = {
                "request_sha256": signature,
                "model": body["model"],
                "num_ctx": options["num_ctx"],
                "num_predict": cap,
            }
            started = time.monotonic()
            try:
                r = request(11434, "/api/chat", body, 120)
                calls = r.get("message", {}).get("tool_calls", [])
                row.update(
                    status=200,
                    prompt_tokens=r.get("prompt_eval_count"),
                    reply_tokens=r.get("eval_count"),
                    done_reason=r.get("done_reason"),
                )
                if len(calls) == 1 and calls[0]["function"]["name"] == "compact":
                    summary = calls[0]["function"]["arguments"].get("summary")
                    if isinstance(summary, str):
                        row["summary_characters"] = len(summary)
            except ServiceError as exc:
                row.update(status=exc.status, incomplete_compact=exc.detail == INCOMPLETE_COMPACT)
            row["seconds"] = round(time.monotonic() - started, 2)
            print(json.dumps(row), file=out, flush=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("private_request", type=Path)
    cli.add_argument("output", type=Path)
    cli.add_argument("--caps", type=int, nargs="+", default=[240, 480, 80, 240, 410, 819, 512])
    a = cli.parse_args()
    measure(a.private_request, a.output, a.caps)
