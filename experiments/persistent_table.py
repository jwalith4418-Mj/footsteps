"""A three-seat game with independent private sessions sharing one local inference queue."""

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from random import Random
from time import monotonic

from experiments.persistent_listener import live_table, measured_step, public_call
from footsteps.decision_notes import open_private
from footsteps.ollama import request
from footsteps.record import read, starting_game
from footsteps.session import Session
from footsteps.table import Table


def play_seat(seat, model, queue, log, trace, context):
    session = Session(seat, inspect_rotations=True, movement_context=True, context=context)
    queued = 0

    def infer(port, path, body, budget):
        submitted = monotonic()

        def generate():
            nonlocal queued
            queued = monotonic() - submitted
            if queued >= budget:
                raise TimeoutError("inference queue consumed this request's budget")
            return request(port, path, body, budget - queued)

        return queue.submit(generate).result()

    while session.snap["phase"] != "over":
        queued = 0
        row = measured_step(session, model, infer=infer, budget=45)
        if row:
            print(json.dumps(row), file=trace, flush=True)
            public = public_call(row, model, False)
            public["queue_seconds"] = round(queued, 3)
            print(json.dumps(public), file=log, flush=True)


def play(root, private, model, context):
    private.mkdir(exist_ok=False)
    table = Table(
        {
            "roles": ["blue", "red", "blue"],
            "start": [-2, 0],
            "goal": [0, 0],
            "hands": [[40, 0], [65, 0], [68, 0]],
            "store": [65, 40, 255],
        },
        Random(103),
        seconds=45,
        discussion=15,
    )
    with (
        live_table(root, table, model, context=context) as (_, seats),
        ThreadPoolExecutor(1) as queue,
    ):

        def run(i):
            with (
                (root / f"seat-{i}.jsonl").open("x") as log,
                open_private(private / f"seat-{i}.jsonl") as trace,
            ):
                play_seat(seats[i], model, queue, log, trace, context)

        with ThreadPoolExecutor(3) as clients:
            list(clients.map(run, seats))


def report(root):
    r = read(root / "game.json")
    g = starting_game(r)
    owed = Counter()
    missed = Counter()
    for e in r["events"]:
        kind = e["kind"]
        if kind in ("eliminate_vote", "move_vote"):
            for seat, vote in zip(g.alive, e["votes"], strict=True):
                owed[seat] += 1
                missed[seat] += vote is None
        elif kind != "draw":
            seat = g.queue[0] if kind == "nominate" else g.actor
            owed[seat] += 1
            missed[seat] += bool(e.get("timeout"))
        g.apply(e)
    assert g.winner
    print("Winner", g.winner, "turn", g.turn, "marker", g.marker)
    for i in range(3):
        calls = list(map(json.loads, (root / f"seat-{i}.jsonl").read_text().splitlines()))
        print(
            i,
            g.roles[i],
            "timely",
            owed[i] - missed[i],
            "/",
            owed[i],
            "requests",
            len(calls),
            "tools",
            dict(Counter(r["tool"] for r in calls)),
            "rejected or failed",
            sum(r["error"] for r in calls),
            "seconds queued",
            round(sum(r["queue_seconds"] for r in calls), 1),
            "request seconds including queue",
            round(sum(r["inference_seconds"] for r in calls), 1),
        )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=Path)
    cli.add_argument(
        "private", type=Path, nargs="?", help="new private directory; omit for offline report"
    )
    cli.add_argument("--model", default="footsteps-qwen3.8:27b-rana-layout")
    cli.add_argument("--context", type=int, choices=(4096, 8192), default=8192)
    args = cli.parse_args()
    if args.private:
        play(args.root, args.private, args.model, args.context)
    report(args.root)
