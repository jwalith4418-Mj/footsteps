"""Measure user-message tokens on the same frozen decisions with the model's GGUF vocabulary."""

import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path
from random import Random

from experiments.model_solitaire import payload
from experiments.spoke_chart import seat_chart as spoke_chart
from footsteps.record import read
from footsteps.table import Table


def measurements(path, tokenizer, gguf):
    record = read(path)
    table = Table(record["setup"], Random(0))
    table.started = True
    for n, event in enumerate(record["events"], 1):
        state = table.game.view(0)
        if state["stage"] in ("place", "discard", "propose"):
            choices = table.choices(0, 0)
            direct = payload(state, choices, "test")["messages"][1]["content"]
            compact = payload(state, choices, "test", chart=True)["messages"][1]["content"]
            without_tiles = compact.split("\n\n", 1)[0]
            spokes = spoke_chart(state)
            variants = {
                "json": direct,
                "json_plus_spokes": direct + "\n\n" + spokes,
                "spokes": without_tiles + "\n\n" + spokes,
                "vertices": compact,
            }
            counts = []
            for message in variants.values():
                ids = subprocess.check_output(
                    [tokenizer, "-m", gguf, "--stdin", "--ids", "--log-disable"],
                    input=message,
                    text=True,
                )
                counts.append(len(json.loads(ids)))
            yield [n, state["turn"], state["stage"], len(state["board"]), *counts]
        table.commit(event)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("record", type=Path)
    cli.add_argument("--tokenizer", default="llama-tokenize")
    cli.add_argument("--gguf", required=True)
    args = cli.parse_args()
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(
        ["event", "turn", "stage", "tiles", "json", "json_plus_spokes", "spokes", "vertices"]
    )
    for row in measurements(args.record, args.tokenizer, args.gguf):
        writer.writerow(row)
        sys.stdout.flush()
