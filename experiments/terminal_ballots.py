"""Repeat two real EXIT ballots with the archived option order and independent role/label cues."""

import argparse
import json
from io import StringIO
from itertools import product
from pathlib import Path

from experiments.action_probe import position
from experiments.goal_pursuit import decide
from experiments.native_summary import rows
from experiments.skill_probe import MODEL


class BallotOrder:
    def __init__(self, first_vote):
        self.first_vote = first_vote

    def shuffle(self, choices):
        choices.sort(key=lambda pair: pair[0]["vote"] != self.first_vote)


def panel(model, conditions):
    games = Path(__file__).with_name("goal-pursuit") / "games"
    for case, seats in (("four-9501-brief", (1, 2)), ("five-9901-brief", (1, 3))):
        source = games / f"{case}.json"
        record = json.loads(source.read_text())
        revision = len(record["events"]) - 1
        assert record["events"][revision]["kind"] == "move_vote"
        receipts = {
            r["seat"]: r
            for r in rows(source.with_suffix(".calls.jsonl"))
            if r["revision"] == revision
        }
        for seat in seats:
            snap = position(source, revision, seat)
            assert snap["state"]["pending"] == snap["state"]["goal"]
            original = receipts[seat]["calls"][-1]["candidates"]
            order = BallotOrder(original["P1"][0]["vote"])
            for prefix, arm in conditions:
                trace, note = [], StringIO()
                row = {
                    "case": case,
                    "event": revision + 1,
                    "seat": seat,
                    "role": snap["state"]["role"],
                    "action_prefix": prefix,
                    "arm": arm,
                    "calls": trace,
                    "vote": None,
                }
                try:
                    row["vote"] = decide(
                        snap, model, note, trace, arm=arm, order=order, action_prefix=prefix
                    )["vote"]
                    row["private_reason"] = json.loads(note.getvalue())["reason"]
                except (OSError, ValueError) as exc:
                    row["error"] = str(exc)
                yield row


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("--model", default=MODEL)
    group = cli.add_mutually_exclusive_group()
    group.add_argument(
        "--literal",
        action="store_true",
        help="use descriptive ballot actions without a role reminder",
    )
    group.add_argument(
        "--binary", action="store_true", help="return the actual Yes/No ballot as a boolean"
    )
    group.add_argument(
        "--voter", action="store_true", help="bind the seat and its private team together once"
    )
    args = cli.parse_args()
    conditions = tuple(product(("P", "A"), ("brief", "personal")))
    if args.literal:
        conditions = (("literal", "named-ballot"), ("literal", "public-result"))
    if args.binary:
        conditions = (("boolean", "binary"), ("boolean", "binary-reason-first"))
    if args.voter:
        conditions = (("boolean", "voter"),)
    with args.output.open("x") as out:
        for row in panel(args.model, conditions):
            out.write(json.dumps(row, separators=(",", ":")) + "\n")
            out.flush()
