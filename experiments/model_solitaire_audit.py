"""Check archived solitaire scores, model fallbacks, chance and rotated game histories."""

import argparse
import csv
from collections import Counter
from pathlib import Path
from random import Random

from footsteps.board import distance, rotate
from footsteps.game import Game
from footsteps.record import read
from footsteps.solo import sealed, setup, simulate


def clockwise(point):
    return point[1], -point[0]


def rotate_event(event):
    if event["kind"] == "place":
        return {**event, "at": clockwise(event["at"]), "rotation": (event["rotation"] + 1) % 4}
    if event["kind"] == "propose" and event["to"] is not None:
        return {**event, "to": clockwise(event["to"])}
    return event


def scores(game):
    return (
        int(game.winner == "good"),
        game.turn,
        distance(game.marker, game.goal),
        int(sealed(game.board, game.marker, game.goal)),
    )


def audit(folder):
    with (folder / "results.csv").open(newline="") as handle:
        results = list(csv.DictReader(handle))
    controls = {"random", "greedy", "exits", "route"}
    players = {row["player"] for row in results}
    if not controls <= players or len(players - controls) != 1:
        raise ValueError(f"{folder}: expected one model and four scripted controls")
    total_calls = 0
    events_checked = 0
    for path in sorted(folder.glob("game-*.json")):
        seed = int(path.stem.split("-")[1])
        record = read(path)
        initial = setup(seed, (4, 2), 2, 10, 0.55)
        if initial != record["setup"]:
            raise ValueError(f"{path}: initial deal differs")
        game = Game(initial)
        turned = Game({**initial, "goal": clockwise(initial["goal"])})
        rng = Random(f"draw/{seed}")
        with (folder / f"calls-{seed}.csv").open(newline="") as handle:
            calls = list(csv.DictReader(handle))
        remaining_calls = iter(calls)
        for index, event in enumerate(record["events"], 1):
            if game.stage == "draw":
                if event["tiles"] != rng.sample(game.store, min(2, len(game.store))):
                    raise ValueError(f"{path} event {index}: draw differs")
            elif game.stage == "move_vote":
                if event["votes"] != [True]:
                    raise ValueError(f"{path} event {index}: solitaire movement veto")
            else:
                call = next(remaining_calls, None)
                if not call or (int(call["event"]), call["stage"], bool(call["error"])) != (
                    index,
                    game.stage,
                    event.get("timeout", False),
                ):
                    raise ValueError(f"{path} event {index}: call log differs")
            game.apply(event)
            turned.apply(rotate_event(event))
            rotated_board = {clockwise(p): rotate(face, 1) for p, face in game.board.items()}
            if (turned.board, turned.marker, turned.stage, turned.winner) != (
                rotated_board,
                clockwise(game.marker),
                game.stage,
                game.winner,
            ):
                raise ValueError(f"{path} event {index}: rotated history diverged")
        if next(remaining_calls, None) is not None or not game.winner:
            raise ValueError(f"{path}: incomplete game or surplus calls")
        summary = [r for r in results if int(r["seed"]) == seed]
        if len(summary) != 5 or {r["player"] for r in summary} != players:
            raise ValueError(f"{path}: missing or duplicate comparison")
        for row in summary:
            observed = tuple(
                int(row[k]) for k in ("win", "turns", "end_distance", "sealed", "fallback")
            )
            if row["player"] in controls:
                ref, _ = simulate(initial, seed, row["player"])
                expected = tuple(ref[k] for k in ("win", "turns", "end_distance", "sealed")) + (0,)
            else:
                expected = (*scores(game), sum(bool(c["error"]) for c in calls))
            if observed != expected:
                raise ValueError(f"{path}: scores differ for {row['player']}")
        total_calls += len(calls)
        events_checked += len(record["events"])
    if Counter(int(r["seed"]) for r in results) != Counter(
        {int(p.stem.split("-")[1]): 5 for p in folder.glob("game-*.json")}
    ):
        raise ValueError(f"{folder}: result seeds differ from games")
    return total_calls, events_checked


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("folders", type=Path, nargs="+")
    for folder in cli.parse_args().folders:
        calls, events = audit(folder)
        print(
            f"{folder.name}: {calls} decisions, {events} referee events checked against a rotated game"
        )
