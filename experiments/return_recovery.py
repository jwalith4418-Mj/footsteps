"""Try two error replies after the same scripted series of invalid return calls."""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.game_efficiency import MODEL, ControlSession, deal
from experiments.persistent_proposals import FixtureSeat
from footsteps.ollama import request
from footsteps.session import Session
from footsteps.table import Table


class ErrorExperimentSession(ControlSession):
    name_available = False

    def execute(self, name, args, offered, revision):
        if not self.name_available:
            return super().execute(name, args, offered, revision)
        if not any(t["function"]["name"] == name for t in offered):
            # Preserve the original error text for this frozen experiment.
            names = ", ".join(t["function"]["name"] for t in offered)
            raise ValueError("Choose one of the currently offered functions: " + names)
        return Session.execute(self, name, args, offered, revision)


def prepared(depth, named):
    table = Table(deal("social", 11301), Random("draw/11301"), 45, 30)
    seat = FixtureSeat(table)
    for i in (1, 2):
        table.join(i, 0)
    session = ErrorExperimentSession(
        seat, context=32768, movement_context=True, inspect_rotations=True, sleep=seat.expire
    )

    def scripted(name, **args):
        row = session.step(
            MODEL,
            infer=lambda *_: {
                "message": {"tool_calls": [{"function": {"name": name, "arguments": args}}]}
            },
        )
        return row["result"]

    piece = next(h for h, (face, _) in session.snap["pieces"].items() if face == 41)
    assert scripted("place_tile", piece=piece, x=-1, y=0)["accepted"]
    assert table.game.stage == "discard"
    held = next(iter(session.snap["pieces"]))
    for _ in range(depth - 1):
        assert "error" in scripted("discard_tile", piece=held)
    # Only the last scripted error and subsequent unavailable tools use the treatment.
    session.name_available = named
    assert "error" in scripted("discard_tile", piece=held)
    return session


def measure(output):
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
        for depth in (1, 6, 16):
            for named in (True, False) if depth == 6 else (False, True):
                session = prepared(depth, named)
                calls = []
                for _ in range(5):
                    row = session.step(MODEL, budget=45)
                    calls.append(
                        {
                            "tool": row["tool"]
                            if row["tool_offered"]
                            else "unavailable_or_incomplete",
                            "error": "error" in row["result"],
                            "seconds": row["inference_seconds"],
                        }
                    )
                    if session.seat.table.game.stage != "discard":
                        break
                event = session.seat.table.record["events"][-1]
                print(
                    json.dumps(
                        {
                            "prior_attempts": depth,
                            "named": named,
                            "calls": calls,
                            "returned": event["kind"] == "discard"
                            and not event.get("timeout", False),
                        }
                    ),
                    file=out,
                    flush=True,
                )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    measure(cli.parse_args().output)
