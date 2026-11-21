"""Compare movement updates from clones of exactly the same scripted build conversation."""

import argparse
import json
import time
from copy import deepcopy
from pathlib import Path

from experiments.persistent_panel import corridor
from footsteps.ollama import request
from footsteps.record import replay
from footsteps.session import Session


class FixtureSeat:
    """Transport the focal seat's JSON projection at a fixed referee time for paired prompts."""

    def __init__(self, table):
        self.table = table
        self.now = 0
        self.table.join(0, 0)

    def call(self, path, data=None):
        if path == "/orient":
            self.table.orient(0, data["revision"], data["piece"], data["rotation"], self.now)
        elif path == "/choice":
            self.table.submit(0, data["revision"], data["choice"], self.now)
        elif path != "/session":
            raise ValueError(path)
        return json.loads(json.dumps(self.table.view(0, self.now, structured_history=True)))

    def expire(self, _):
        # Choosing wait while owing this decision expires it as it would at a quiet one-seat table.
        self.now = self.table.deadline


def prepared(heading):
    seat = FixtureSeat(corridor(heading))
    session = Session(seat, sleep=seat.expire, inspect_rotations=True)
    x, y = seat.table.game.start
    midpoint = {"x": x // 2, "y": y // 2}
    piece = {"piece": "H1"}
    for name, args in [
        ("inspect_rotations_at", piece | midpoint),
        ("orient_tile", piece | {"rotation": {"east": 3, "north": 2, "west": 1}[heading]}),
        ("place_tile", piece | midpoint),
        ("return_tile", {"piece": "H2"}),
    ]:

        def scripted(*_, n=name, a=args):
            return {"message": {"tool_calls": [{"function": {"name": n, "arguments": a}}]}}

        row = session.step("script", infer=scripted)
        assert "error" not in row["result"]
    assert seat.table.game.stage == "propose"
    return session, [midpoint["x"], midpoint["y"]]


def run(path, model):
    request(
        11434,
        "/api/chat",
        {"model": model, "messages": [], "stream": False, "options": {"num_ctx": 8192}},
        120,
    )
    with path.open("x") as out:
        for heading in ("east", "north", "west"):
            original, midpoint = prepared(heading)
            for show in (True, False) if heading == "north" else (False, True):
                s = deepcopy(original)
                s.movement_context = show
                calls = []
                end = time.monotonic() + 30
                while (
                    s.seat.table.game.stage == "propose" and (budget := end - time.monotonic()) > 0
                ):
                    try:
                        row = s.step(model, budget=budget)
                    except TimeoutError:
                        break
                    calls.append(
                        {
                            k: row[k]
                            for k in ("tool", "prompt_tokens", "reply_tokens", "inference_seconds")
                        }
                        | {"error": row["result"].get("error")}
                    )
                if s.seat.table.game.stage == "propose":
                    s.seat.expire(0)
                    s.refresh()
                print(
                    json.dumps(
                        {
                            "heading": heading,
                            "show_landings": show,
                            "model": model,
                            "midpoint": midpoint,
                            "calls": calls,
                            "record": s.seat.table.record,
                        }
                    ),
                    file=out,
                    flush=True,
                )


def report(path):
    for row in map(json.loads, path.read_text().splitlines()):
        r = row["record"]
        replay(r)
        choice = next(e for e in r["events"] if e["kind"] == "propose")
        print(
            row["heading"],
            row["show_landings"],
            choice,
            choice["to"] == row["midpoint"],
            [c["tool"] for c in row["calls"]],
        )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("path", type=Path)
    cli.add_argument("--model", help="run the panel on a local model; omit for an offline audit")
    args = cli.parse_args()
    if args.model:
        run(args.path, args.model)
    report(args.path)
