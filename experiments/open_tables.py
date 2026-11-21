"""Run a fresh social deal with independent persistent seats and the ordinary live prompt."""

import argparse
from pathlib import Path
from random import Random

from experiments.game_efficiency import MODEL
from experiments.persistent_table import play
from footsteps.game import with_exit_origin
from footsteps.table import Table, paper_setup

DEALS = {"three": (13401, 3, [2, 0], 4), "four": (13402, 4, [2, 1], 6)}


def run(name, root, private):
    seed, seats, offset, size = DEALS[name]
    setup = paper_setup(Random(seed), seats)
    setup.update(goal=offset, store=setup["store"][:size])
    table = Table(with_exit_origin(setup), Random(f"draw/{seed}"), 60, 30, early_ballot=True)
    play(root, private, MODEL, 16384, 60, 30, table=table)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("deal", choices=DEALS)
    cli.add_argument("root", type=Path)
    cli.add_argument("private", type=Path)
    args = cli.parse_args()
    run(args.deal, args.root, args.private)
