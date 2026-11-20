"""Summarize counterbalanced replies and good builders' votes on their own closer moves."""

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from footsteps.board import distance
from footsteps.game import Game
from footsteps.record import read


def probe_counts(files):
    pairs = defaultdict(dict)
    for path in files:
        with path.open(newline="") as handle:
            for r in csv.DictReader(handle):
                key = r["model"], r["encoding"], r["case"], r["seat"], r["preferred"]
                if r["first"] in pairs[key]:
                    raise ValueError(f"duplicate response for {key}")
                pairs[key][r["first"]] = r["choice"]
    for (model, encoding, case, seat, preferred), pair in pairs.items():
        if pair.keys() != {"True", "False"}:
            raise ValueError(f"incomplete pair for {(model, encoding, case, seat)}")
        yield model, encoding, case, preferred, pair["True"], pair["False"]


def self_votes(path):
    record = read(path)
    game = Game(record["setup"])
    votes = []
    for event in record["events"]:
        if (
            game.stage == "move_vote"
            and game.roles[game.actor] == "good"
            and distance(game.pending, game.goal) < distance(game.marker, game.goal)
        ):
            votes.append(event["votes"][game.alive.index(game.actor)])
        game.apply(event)
    return votes


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("folder", type=Path)
    folder = cli.parse_args().folder
    counts = defaultdict(lambda: [0, 0, 0, 0])
    for model, encoding, case, preferred, normal, reverse in probe_counts(
        [folder / "probe.csv", folder / "preview.csv"]
    ):
        group = counts[(model, encoding, "control" if preferred else "recorded")]
        group[0] += 1
        group[1] += normal != reverse
        group[2] += normal == preferred
        group[3] += reverse == preferred
    print("model encoding positions pairs flips correct-normal correct-reverse")
    for key, (pairs, flips, normal, reverse) in sorted(counts.items()):
        print(
            *key,
            pairs,
            flips,
            normal if key[-1] == "control" else "-",
            reverse if key[-1] == "control" else "-",
        )
    print("game good-closer-self-no missing total")
    for path in sorted(folder.glob("*/game.json")):
        votes = self_votes(path)
        print(path.parent.name, votes.count(False), votes.count(None), len(votes))
