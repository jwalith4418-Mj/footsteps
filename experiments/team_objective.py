"""Vary only the persistent system instruction on matched, sealed EXIT ballots."""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.game_efficiency import MODEL, ControlSession
from experiments.persistent_proposals import FixtureSeat
from footsteps.ollama import request
from footsteps.record import read
from footsteps.table import Table

SOURCE = Path(__file__).parent / "game-efficiency/social-control/game.json"
SHORT = "Your only objective is for your team to win the game."
ZERO_SUM = (
    "This is a zero-sum game. Avoid actions that put your team in a losing state "
    "or give your opponents a way to win."
)
ARMS = {"control": "", "objective": SHORT, "objective-and-risk": SHORT + " " + ZERO_SUM}


def ballot(voter, team, arm, *, remarks=False):
    record = read(SOURCE)
    setup = record["setup"]
    setup["roles"] = ["blue"] * 3
    setup["roles"][voter if team == "red" else 1 - voter] = "red"
    table = Table(setup, Random(11301), seconds=45, discussion=30 if remarks else 0)
    for event in record["events"][:-1]:
        table.commit(event)
    assert table.game.stage == "move_vote" and table.game.pending == table.game.goal
    peer = FixtureSeat(table, voter)
    others = [i for i in range(3) if i != voter]
    for i in others:
        table.join(i, 0)
    if remarks:
        for row in record["remarks"]:
            if row["after_event"] == table.revision:
                table.say(row["seat"], table.revision, row["text"], 0)
        peer.now = 30
    for i, vote in zip(others, (True, False), strict=True):
        table.submit(i, table.revision, {"vote": vote}, peer.now)
    session = ControlSession(
        peer, sleep=peer.expire, inspect_rotations=True, movement_context=True, context=32768
    )
    instruction = (
        f"Your only objective is for {session.role()['team'].title()} to win the game."
        if arm == "named-team"
        else ARMS[arm]
    )
    if instruction:
        message = session.messages[0]
        identity, rules = message["content"].split(". ", 1)
        message["content"] = f"{identity}. {instruction} {rules}"
    return session


def measure(output, remarks, named_only):
    request(
        11434,
        "/api/chat",
        {
            "model": MODEL,
            "messages": [],
            "stream": False,
            "options": {"num_ctx": 32768},
            "keep_alive": "10m",
        },
        120,
    )
    with output.open("x") as out:
        for case, (voter, team) in enumerate(((1, "red"), (0, "blue"), (1, "blue"), (0, "red"))):
            arms = list(ARMS)
            for arm in ["named-team"] if named_only else arms[case % 3 :] + arms[: case % 3]:
                session = ballot(voter, team, arm, remarks=remarks)
                table = session.seat.table
                rev = table.revision
                calls = []
                for _ in range(5):
                    row = session.step(MODEL, budget=45)
                    calls.append(
                        row["tool"] if row.get("tool_offered") else "unavailable_or_incomplete"
                    )
                    if table.revision != rev:
                        break
                vote = (
                    None if table.revision == rev else table.record["events"][rev]["votes"][voter]
                )
                print(
                    json.dumps(
                        {
                            "seat": voter,
                            "team": team,
                            "builder": 1,
                            "arm": arm,
                            "tools": calls,
                            "vote": vote,
                            "team_aligned": vote is (team == "blue"),
                        }
                    ),
                    file=out,
                    flush=True,
                )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("--exit-remarks", action="store_true")
    cli.add_argument("--named-only", action="store_true")
    args = cli.parse_args()
    measure(args.output, args.exit_remarks, args.named_only)
