"""Check a role-specific objective against the 14101 proposal, votes and a directed trap."""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.ballot_thinking import position
from experiments.game_efficiency import MODEL
from experiments.persistent_proposals import FixtureSeat
from footsteps.record import read
from footsteps.session import Session
from footsteps.table import Table

SOURCE = Path(__file__).parent / "nomination-publicity/14101/game.json"
CASES = (
    ("proposal", 1),
    ("proposal-blue", 1),
    ("exit", 0),
    ("exit", 1),
    ("exit", 2),
    ("wrong-summary", 0),
    ("trap-red", 1),
    ("trap-blue", 1),
)


def crossing(case, seat):
    record = read(SOURCE)
    if case == "proposal-blue":
        roles = record["setup"]["roles"]
        roles[1], roles[2] = roles[2], roles[1]
    table = Table(record["setup"], Random("draw/14101"), seconds=60, discussion=30)
    peer = FixtureSeat(table, seat)
    for i in range(4):
        table.join(i, 0)
    assert table.record["events"] == record["events"][:1]
    cut = 12 if case.startswith("proposal") else 13
    for event in record["events"][1:cut]:
        table.commit(event)
        if table.game.stage == "move_vote":
            table.open_decision(0)
            for remark in record["remarks"]:
                if remark["after_event"] == table.revision:
                    table.say(remark["seat"], table.revision, remark["text"], 0)
    peer.now = table.opens
    session = Session(
        peer, sleep=peer.expire, context=16384, inspect_rotations=True, movement_context=True
    )
    if case == "wrong-summary":
        session.summary = "I am Red. Entering EXIT wins for Red. Vote Yes."
        session.reset()
    return session


def trial(case, seat):
    if case.startswith("trap-"):
        _, session = position("trap", case.removeprefix("trap-"))
    else:
        session = crossing(case, seat)
    table = session.seat.table
    revision = table.revision
    calls = []
    choice = None
    for _ in range(5):
        row = session.step(MODEL, budget=60)
        if row is None:
            break
        calls.append(
            {
                "tool": row["tool"] if row.get("tool_offered") else None,
                "tokens": row.get("reply_tokens"),
                "seconds": row.get("inference_seconds"),
            }
        )
        if row["result"].get("accepted"):
            if row["tool"] == "vote_move":
                choice = table.votes[seat]
            elif row["tool"] in ("stay", "propose_step"):
                event = table.record["events"][revision]
                choice = event["to"] if event["to"] is not None else "stay"
            break
        if table.revision != revision:
            break
    team = table.game.roles[seat]
    if choice is None:
        aligned = False
    elif case.startswith("proposal"):
        aligned = (choice == list(table.game.goal)) == (team == "blue")
    else:
        aligned = choice is ((team == "blue") != case.startswith("trap-"))
    return {
        "case": case,
        "seat": seat,
        "team": team,
        "choice": choice,
        "aligned": aligned,
        "calls": calls,
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    with args.output.open("x") as out:
        for case, seat in CASES:
            print(json.dumps(trial(case, seat)), file=out, flush=True)
