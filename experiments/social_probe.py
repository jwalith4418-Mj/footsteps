"""Fork a real opening at its first movement vote and query only P0's private view."""

import argparse
from copy import deepcopy
from pathlib import Path
from random import Random

from experiments.skill_probe import MODEL
from experiments.social_evidence import approach, write_rows
from experiments.social_prompt import social_choice
from footsteps.decision_notes import open_private
from footsteps.record import read
from footsteps.table import Table


def nomination(record, dissenter):
    table = Table(record["setup"], Random(1), discussion=1)
    table.started = True
    for event in record["events"]:
        if event["kind"] == "move_vote":
            assert table.game.turn == 1 and approach(table.game.view(0))
            table.commit({"kind": "move_vote", "votes": [s != dissenter for s in range(3)]})
            break
        table.commit(event)
    else:
        raise ValueError("need a three-seat opening with a progress vote on turn one")
    table.open_decision(0)
    for s in (1, 2):
        assert table.game.queue[0] == s
        table.submit(s, table.revision, {"target": None}, table.opens)
    return table


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("game", type=Path)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument("--arm", choices=("base", "focused", "ledger", "receipt"), required=True)
    cli.add_argument(
        "--claims", action="store_true", help="script one public accusation per ballot"
    )
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--private-notes", type=Path, required=True)
    args = cli.parse_args()
    rows = []
    record = read(args.game)
    with open_private(args.private_notes) as notes:
        for dissenter in (None, 1, 2):
            nom = nomination(record, dissenter)
            for target in (None, 1, 2):
                if (args.claims or args.arm == "receipt") and target is None:
                    continue
                fork = deepcopy(nom)
                if target is not None:
                    fork.submit(0, fork.revision, {"target": target}, fork.opens)
                    if args.claims:
                        fork.say(
                            3 - target,
                            fork.revision,
                            f"P{target} voted no on our move toward EXIT. Vote to remove P{target}.",
                            fork.opens - fork.discussion,
                        )
                snap = fork.view(0, fork.opens)
                for reverse in (False, True):
                    choice = social_choice(snap, args.model, args.arm, notes, reverse=reverse)
                    rows.append(
                        {
                            "dissenter": dissenter,
                            "target": target,
                            "reverse": reverse,
                            "claim": args.claims,
                            "arm": args.arm,
                            "choice": next(iter(choice.values())),
                        }
                    )
    write_rows(args.out, rows)


if __name__ == "__main__":
    main()
