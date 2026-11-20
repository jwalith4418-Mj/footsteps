"""Can the three surviving Blue seats reach EXIT after Red is removed on turn one?"""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.offsets import POLICIES, play_out
from footsteps.game import Game
from footsteps.record import read, replay


def run(source, output):
    record = read(source)
    for policy in POLICIES:
        wins = 0
        for seed in range(64):
            branch = {
                **record,
                "events": list(record["events"][:11]),
                "remarks": [r for r in record["remarks"] if r["after_event"] < 11],
            }
            branch.pop("table_id")
            game = Game(branch["setup"])
            draws = Random("draw/8602")
            for e in branch["events"]:
                if e["kind"] == "draw":
                    assert e["tiles"] == draws.sample(game.store, min(2, len(game.store)))
                game.apply(e)
            assert game.stage == "draw" and game.alive == [0, 2, 3]
            play_out(game, branch, policy, draws, Random(seed))
            assert branch["events"][11] == record["events"][11]
            if replay(branch).winner == "good":
                if not wins and policy == "exits":
                    output.write_text(json.dumps(branch, separators=(",", ":")) + "\n")
                wins += 1
        print(policy, wins, "/ 64")


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("source", type=Path)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    run(args.source, args.output)
