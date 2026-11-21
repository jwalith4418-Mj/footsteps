"""A three-seat game with independent private sessions sharing one local inference queue."""

import argparse
import json
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from pathlib import Path
from random import Random
from time import monotonic

from experiments.persistent_runtime import live_table, measured_step, public_call, resident_model
from footsteps.decision_notes import open_private
from footsteps.ollama import request
from footsteps.record import read, starting_game
from footsteps.session import CONTEXT_WINDOWS, Session
from footsteps.table import Table


def speaking_seconds(seat, revision):
    view = seat.call("/session")
    if view["revision"] == revision and view["can_speak"]:
        return round(view["seconds_left"], 3)
    return 0


def play_seat(seat, model, queue, log, trace, context, request_budget):
    session = Session(seat, inspect_rotations=True, movement_context=True, context=context)
    queued = 0
    discussion = None

    def infer(port, path, body, budget):
        nonlocal discussion
        submitted = monotonic()
        revision = session.snap["revision"]
        if session.snap["phase"] == "discussion":
            discussion = {
                "revision": revision,
                "offered": any(t["function"]["name"] == "speak" for t in body["tools"]),
            }

        def generate():
            nonlocal queued
            queued = monotonic() - submitted
            if discussion is not None:
                discussion["seconds_at_start"] = speaking_seconds(seat, revision)
            remaining = budget - (monotonic() - submitted)
            if remaining <= 0:
                raise TimeoutError("inference queue consumed this request's budget")
            reply = request(port, path, body, remaining)
            if discussion is not None:
                discussion["seconds_after_reply"] = speaking_seconds(seat, revision)
            return reply

        return queue.submit(generate).result()

    while session.snap["phase"] != "over":
        queued = 0
        discussion = None
        row = measured_step(session, model, infer=infer, budget=request_budget)
        if row:
            print(json.dumps(row), file=trace, flush=True)
            public = public_call(row, model, False)
            public["queue_seconds"] = round(queued, 3)
            public["discussion"] = discussion
            print(json.dumps(public), file=log, flush=True)


def play(root, private, model, context, seconds, discussion_seconds):
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
        seconds=seconds,
        discussion=discussion_seconds,
    )
    with (
        live_table(root, table, model, context=context) as (_, seats),
        ThreadPoolExecutor(1) as queue,
    ):
        start = monotonic()

        def run(i):
            with (
                (root / f"seat-{i}.jsonl").open("x") as log,
                open_private(private / f"seat-{i}.jsonl") as trace,
            ):
                play_seat(seats[i], model, queue, log, trace, context, seconds)

        with ThreadPoolExecutor(3) as clients:
            list(clients.map(run, seats))
        timing = {
            "model": model,
            "num_ctx": context,
            "decision_seconds": seconds,
            "discussion_seconds": discussion_seconds,
            "play_seconds": round(monotonic() - start, 2),
        }
        timing["resident"] = resident_model(model)
        (root / "timing.json").write_text(json.dumps(timing, indent=2) + "\n")


def report(root):
    r = read(root / "game.json")
    g = starting_game(r)
    timing_path = root / "timing.json"
    timing = json.loads(timing_path.read_text()) if timing_path.exists() else {}
    discussion_enabled = timing.get("discussion_seconds") != 0
    owed = Counter()
    missed = Counter()
    windows = {i: [] for i in range(len(g.roles))}
    for revision, e in enumerate(r["events"]):
        kind = e["kind"]
        if kind in ("eliminate_vote", "move_vote"):
            for seat, vote in zip(g.alive, e["votes"], strict=True):
                if discussion_enabled:
                    windows[seat].append(revision)
                owed[seat] += 1
                missed[seat] += vote is None
        elif kind != "draw":
            seat = g.queue[0] if kind == "nominate" else g.actor
            owed[seat] += 1
            missed[seat] += bool(e.get("timeout"))
        g.apply(e)
    assert g.winner
    print("Winner", g.winner, "turn", g.turn, "marker", g.marker)
    latencies = []
    timely_windows = 0
    service_seconds = 0
    compact_seconds = 0
    compactions = 0
    for i in range(3):
        calls = list(map(json.loads, (root / f"seat-{i}.jsonl").read_text().splitlines()))
        for c in calls:
            latencies.append(c["inference_seconds"])
            service = c["inference_seconds"] - c["queue_seconds"]
            service_seconds += service
            if c["tool"] == "compact":
                compactions += 1
                compact_seconds += service
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

        if any("discussion" in call for call in calls):
            for revision in windows[i]:
                offered = [
                    call
                    for call in calls
                    if (d := call["discussion"]) and d["revision"] == revision and d["offered"]
                ]
                ready = [
                    call["tool"]
                    for call in offered
                    if call["discussion"].get("seconds_after_reply", 0) > 0
                ]
                timely_windows += bool(ready)
                print(
                    "  discussion",
                    revision,
                    "offered",
                    len(offered),
                    "replies before close",
                    ready,
                )

    print(
        "compact calls",
        compactions,
        "compact service seconds",
        round(compact_seconds, 1),
        "of all service seconds",
        round(service_seconds, 1),
    )
    if timing:
        print(
            "wall seconds",
            timing["play_seconds"],
            "timely discussion windows",
            timely_windows,
            "/",
            sum(map(len, windows.values())),
            "remarks",
            len(r.get("remarks", [])),
            "timely decisions",
            owed.total() - missed.total(),
            "/",
            owed.total(),
            "requests per minute",
            round(60 * len(latencies) / timing["play_seconds"], 1),
            "p95 seconds including queue",
            sorted(latencies)[ceil(len(latencies) * 0.95) - 1],
        )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=Path)
    cli.add_argument(
        "private", type=Path, nargs="?", help="new private directory; omit for offline report"
    )
    cli.add_argument("--model", default="footsteps-qwen3.8:27b-rana-layout")
    cli.add_argument("--context", type=int, choices=CONTEXT_WINDOWS, default=8192)
    cli.add_argument("--decision-seconds", type=int, default=45)
    cli.add_argument("--discussion-seconds", type=int, default=15)
    args = cli.parse_args()
    if args.private:
        play(
            args.root,
            args.private,
            args.model,
            args.context,
            args.decision_seconds,
            args.discussion_seconds,
        )
    report(args.root)
