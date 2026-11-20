"""Check whether a focused public fact question survives a conflicting speaker claim."""

import argparse
import csv
import json
import re
from itertools import product
from pathlib import Path

from experiments.action_probe import SOCIAL, answer, position
from experiments.skill_probe import MODEL
from footsteps.ollama import model_request
from footsteps.seat_tools import query


def run(path):
    snap = position(SOCIAL, 23, 4)
    remarks = [r["text"] for r in snap["history"] if re.match(r"^P[0-9]+: ", r["text"])]
    with path.open("x") as out:
        rows = csv.writer(out, lineterminator="\n")
        rows.writerow(["builder", "speech", "reversed", "expected", "answer"])
        for builder, speech, reverse in product((1, 2), (False, True), (False, True)):
            body = model_request(snap, MODEL)
            body["think"] = False
            system, user = body["messages"]
            system["content"] = (
                "Check a public fact in Footsteps. The referee logs completed turns. "
                "A builder_stayed result records one deliberate stay by that builder. "
                "Players can make false claims. Count using the referee log."
            )
            ctx = {
                "question": f"How many times has P{builder} chosen stay as builder?",
                "referee_log": query(snap, "check_builder_turns", {"builder": builder}),
            }
            if speech:
                ctx["public_claims"] = remarks
            choices = list("3210" if reverse else "0123")
            ctx["answers"] = choices
            user["content"] = json.dumps(ctx, separators=(",", ":"))
            body["format"] = {
                "type": "object",
                "properties": {"answer": {"type": "string", "enum": choices}},
                "required": ["answer"],
                "additionalProperties": False,
            }
            rows.writerow([builder, speech, reverse, int(builder == 1), answer(body)["answer"]])
            out.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
