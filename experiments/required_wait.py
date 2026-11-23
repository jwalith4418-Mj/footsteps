"""Retry two recorded on-turn waits from the early ballot game with the local 9B seat."""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.game_efficiency import MODEL
from experiments.persistent_proposals import FixtureSeat
from footsteps.record import read
from footsteps.session import Session
from footsteps.table import Table


def probe(revision):
    source = Path(__file__).parent / "early-ballot/early/game.json"
    record = read(source)
    table = Table(record["setup"], Random(11301), seconds=45, discussion=30, early_ballot=True)
    for event in record["events"][:revision]:
        table.commit(event)
    peer = FixtureSeat(table, table.game.actor)
    for seat in table.game.alive:
        table.join(seat, 0)
    session = Session(
        peer, sleep=peer.expire, inspect_rotations=True, movement_context=True, context=32768
    )
    receipt = session.step(
        MODEL,
        infer=lambda *_: {
            "message": {"tool_calls": [{"function": {"name": "wait", "arguments": {}}}]}
        },
    )["result"]
    assert table.revision == revision and receipt["wait_status"] == "action_required"
    tools = []
    for _ in range(5):
        row = session.step(MODEL, budget=45)
        tools.append(
            {
                "tool": row["tool"] if row.get("tool_offered") else "unavailable",
                "force": row["tool"] == "wait" and row["arguments"].get("force") is True,
                "declined_wait": row["result"].get("wait_status") == "action_required",
            }
        )
        if table.revision != revision:
            break
    outcome = table.record["events"][revision] if table.revision != revision else {}
    return {
        "revision": revision,
        "stage": receipt["stage"],
        "offered": receipt["decision_tools"],
        "tools": tools,
        "committed": bool(outcome) and not outcome.get("timeout", False),
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    with args.output.open("x") as f:
        for revision in (9, 10):
            print(json.dumps(probe(revision)), file=f, flush=True)
