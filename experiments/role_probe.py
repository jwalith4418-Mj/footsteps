"""Check role identification separately from behavior, holding every public action fixed."""

import argparse
import csv
import json
from pathlib import Path
from random import Random

from experiments.skill_probe import MODEL
from footsteps.ollama import model_request, request
from footsteps.table import Table, paper_setup


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument("--out", type=Path, required=True)
    args = cli.parse_args()
    request(
        11434,
        "/api/generate",
        {"model": args.model, "stream": False, "options": {"num_ctx": 4096}},
        180,
    )
    with args.out.open("x") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["brief", "roles", "seat", "question", "expected", "answer"])
        for roles in (
            ["red", "blue", "red", "blue"],
            ["blue", "red", "blue", "red"],
            ["red", "blue", "blue", "blue"],
        ):
            setup = paper_setup(Random(8601))
            setup["roles"] = roles
            table = Table(setup, Random(1))
            for s in range(4):
                table.join(s, 0)
            for seat in (0, 1):
                snap = table.view(seat, 0)
                # The nonacting seat can answer a read-only quiz before making any move.
                snap["choices"] = {}
                for brief in ("original", "explicit"):
                    for question, opts, expected in [
                        *[
                            (
                                f"What alignment can you establish for P{target} at setup?",
                                ["blue", "red", "unknown"],
                                roles[target] if roles[seat] == "red" else "unknown",
                            )
                            for target in (2, 3)
                        ],
                        (
                            "Is it common knowledge that each Red player knows every player's alignment?",
                            ["yes", "no", "unknown"],
                            "yes",
                        ),
                    ]:
                        body = model_request(snap, args.model)
                        ctx = json.loads(body["messages"][1]["content"])
                        if brief == "original":
                            del ctx["common_knowledge"], ctx["your_private_role_information"]
                        ctx["question"] = question
                        ctx["options"] = opts
                        body["messages"][0]["content"] = (
                            body["messages"][0]["content"].split("Each field of options")[0]
                            + "Answer the knowledge question using only your seat's information. Select the literal answer name."
                        )
                        body["messages"][1]["content"] = json.dumps(ctx, separators=(",", ":"))
                        body["format"] = {
                            "type": "object",
                            "properties": {"answer": {"type": "string", "enum": opts}},
                            "required": ["answer"],
                            "additionalProperties": False,
                        }
                        body["think"] = False
                        reply = request(11434, "/api/chat", body, 30)
                        answer = json.loads(reply["message"]["content"])["answer"]
                        w.writerow([brief, " ".join(roles), seat, question, expected, answer])
                        f.flush()


if __name__ == "__main__":
    main()
