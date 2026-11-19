"""Audit model calls against each revealed decision and summarize a saved self-play panel."""

import argparse
import csv
import json
import sys
from collections import Counter, defaultdict
from math import ceil
from pathlib import Path

from footsteps.board import connects, distance, moves, neighbors, rotate
from footsteps.game import Game
from footsteps.record import read, replay


def inventory(game):
    return (
        Counter(game.store)
        + Counter(t for h in game.hands for t in h)
        + Counter(face for face, _ in game.placements.values())
    )


def forward_available(game):
    marker, goal = game.marker, game.goal
    for d, p in enumerate(neighbors(marker)):
        if p in game.board or distance(p, goal) >= distance(marker, goal):
            continue
        if any(
            connects(game.board[marker], rotate(t, r), d)
            for t in game.hands[game.actor]
            for r in range(4)
        ):
            return True
    return False


def ballot_timing(rows):
    by_event = defaultdict(list)
    for row in rows:
        if row["stage"].endswith("_vote") and row.get("remaining_ms"):
            by_event[row["event"]].append(row)
    slowest = []
    peak = 0
    for group in by_event.values():
        slowest.append(max(15000 - int(r["remaining_ms"]) + int(r["ms"]) for r in group))
        intervals = [(int(r["start_ms"]), int(r["start_ms"]) + int(r["ms"])) for r in group]
        peak = max(peak, max(sum(a <= start < b for a, b in intervals) for start, _ in intervals))
    return max(slowest, default=None), peak


def summarize(folder):
    record = read(folder / "game.json")
    final = replay(record)
    if not final.winner:
        raise ValueError(f"{folder}: unfinished game")
    with (folder / "calls.csv").open(newline="") as f:
        rows = list(csv.DictReader(f))
    calls = {(int(row["event"]), int(row["seat"])): row for row in rows}
    if len(calls) != len(rows):
        raise ValueError(f"{folder}: repeated inference for the same decision")
    game = Game(record["setup"])
    supply = inventory(game)
    counts = Counter()
    times = []
    best_distance = distance(game.marker, game.goal)
    first_elim_turn = None
    for n, event in enumerate(record["events"], start=1):
        stage, turn = game.stage, game.turn
        if stage.endswith("_vote"):
            choices = {
                p: None if v is None else {"vote": v}
                for p, v in zip(game.alive, event["votes"], strict=True)
            }
        elif stage != "draw":
            seat = game.queue[0] if stage == "nominate" else game.actor
            choices = {
                seat: None
                if event.get("timeout")
                else {k: v for k, v in event.items() if k != "kind"}
            }
        else:
            choices = {}
        for seat, choice in choices.items():
            row = calls.pop((n, seat), None)
            if row:
                if stage != row["stage"]:
                    raise ValueError(f"{folder} event {n}: wrong decision stage")
                times.append(int(row["ms"]))
                counts["errors"] += bool(row["error"])
            if choice is None:
                counts["missing"] += 1
            elif not row or not row["choice"] or json.loads(row["choice"]) != choice:
                raise ValueError(
                    f"{folder} event {n}: P{seat} submitted decision differs from inference"
                )
            counts["decisions"] += 1

        good = game.roles[game.actor] == "good"
        build = good and stage == "place" and forward_available(game)
        if build:
            counts["build_options"] += 1
        old_distance = distance(game.marker, game.goal)
        if (
            good
            and stage == "propose"
            and any(distance(p, game.goal) < old_distance for p in moves(game.board, game.marker))
        ):
            counts["move_options"] += 1
            if event["to"] and distance(event["to"], game.goal) < old_distance:
                counts["proposed"] += 1
        alive = set(game.alive)
        game.apply(event)
        if build:
            at = tuple(event["at"])
            if at in moves(game.board, game.marker) and distance(at, game.goal) < old_distance:
                counts["built"] += 1
        if alive != set(game.alive):
            first_elim_turn = first_elim_turn or turn
            (removed,) = alive - set(game.alive)
            counts[game.roles[removed] + "_out"] += 1
        best_distance = min(best_distance, distance(game.marker, game.goal))
        if inventory(game) != supply:
            raise ValueError(f"{folder} event {n}: tile conservation failed")
    if calls:
        raise ValueError(f"{folder}: calls outside a seat's decision")
    latest, peak = ballot_timing(rows)
    times.sort()
    return {
        "game": folder.name,
        "win": final.winner,
        "turns": final.turn,
        "closest": best_distance,
        "end": distance(final.marker, final.goal),
        "build": f"{counts['built']}/{counts['build_options']}",
        "propose": f"{counts['proposed']}/{counts['move_options']}",
        "first_out": first_elim_turn or "-",
        "good_out": counts["good_out"],
        "bad_out": counts["bad_out"],
        "calls": len(times),
        "errors": counts["errors"],
        "timeouts": counts["missing"],
        "decisions": counts["decisions"],
        "max_ballot_reply_ms": latest,
        "max_overlap": peak or None,
        "p50_ms": times[ceil(len(times) * 0.50) - 1] if times else "-",
        "p95_ms": times[ceil(len(times) * 0.95) - 1] if times else "-",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("panel", type=Path)
    args = parser.parse_args()
    games = sorted(p.parent for p in args.panel.glob("*/game.json"))
    if not games:
        parser.error("no game directories in panel")
    results = [summarize(game) for game in games]
    writer = csv.DictWriter(sys.stdout, fieldnames=results[0], lineterminator="\n")
    writer.writeheader()
    writer.writerows(results)
