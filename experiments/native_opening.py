"""Does asking for the first native call explicitly avoid an empty, token-limited opening?"""

import argparse
import json
from pathlib import Path
from time import monotonic

from experiments.native_probe import panel
from experiments.native_transfer import transfer_panel
from experiments.skill_probe import MODEL
from footsteps.action_tools import action_request, build_tools
from footsteps.ollama import request


def run(path, model):
    positions = list(panel()) + list(transfer_panel())
    sample = {"Blue-82-escape", "Red-guest", "held-9600-E10-good", "held-9600-E10-bad"}
    with path.open("x") as out:
        for idx, (name, snap, _, _) in enumerate(p for p in positions if p[0] in sample):
            tools = build_tools(snap, "hand")
            arms = ["original", "cue", "longer"]
            for offset in range(len(arms)):
                arm = arms[(idx + offset) % len(arms)]
                body = action_request(snap, model, tools, cue=arm == "cue")
                if arm == "longer":
                    body["options"]["num_predict"] = 768
                log = {"case": name, "arm": arm, "model": model}
                start = monotonic()
                try:
                    reply = request(11434, "/api/chat", body, 30)
                    message = reply["message"]
                    calls = message.get("tool_calls", [])
                    log.update(
                        done=reply.get("done_reason"),
                        names=[c["function"]["name"] for c in calls],
                        output_tokens=reply.get("eval_count"),
                        content_chars=len(message.get("content", "")),
                        thinking_chars=len(message.get("thinking", "")),
                    )
                except (OSError, ValueError) as exc:
                    log["error"] = str(exc)
                log["seconds"] = round(monotonic() - start, 3)
                out.write(json.dumps(log, separators=(",", ":")) + "\n")
                out.flush()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("--model", default=MODEL)
    args = cli.parse_args()
    run(args.output, args.model)
