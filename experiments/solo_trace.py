"""Locate unused placements, stays and trap entries in saved solitaire decisions."""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path
from random import Random

from experiments.model_solitaire import geometry
from footsteps.board import distance, moves, rotate
from footsteps.record import read
from footsteps.solo import sealed
from footsteps.table import Table


def decisions(path):
    record = read(path)
    if record["setup"]["roles"] != ["good"]:
        raise ValueError("expected a one-seat solitaire record")
    table = Table(record["setup"], Random(0))
    table.started = True
    game = table.game
    for n, event in enumerate(record["events"], 1):
        stage = game.stage
        row = None
        if stage in ("place", "propose"):
            board, goal, marker = game.board, game.goal, game.marker
            previously_sealed = sealed(board, marker, goal)
            row = {
                "arm": path.parent.name,
                "game": path.stem,
                "event": n,
                "turn": game.turn,
                "stage": stage,
                "timeout": event.get("timeout", False),
                "choice": "",
                "options": "",
                "alternative": "",
                "outcome": "",
            }
            if stage == "place":
                chosen = (tuple(event["at"]), event["tile"], event["rotation"])
                row["choice"] = list(chosen)
                candidates = []
                for square in geometry(game.view(0), table.choices(0, 0))[
                    "placements_next_to_marker"
                ]:
                    if square["distance"] >= distance(marker, goal):
                        continue
                    pos = tuple(map(int, square["at"].split(",")))
                    for face, rotation, _ in square["enterable_builds"]:
                        trial = {**board, pos: rotate(face, rotation)}
                        if not sealed(trial, pos, goal):
                            candidates.append((pos, face, rotation))
                row["options"] = len(candidates)
                if candidates:
                    row["outcome"] = "used_build" if chosen in candidates else "other_build"
                    row["alternative"] = list(candidates[0])
                else:
                    row["outcome"] = "no_build"
            else:
                destinations = moves(board, marker)
                safe_closer = [
                    p
                    for p in destinations
                    if distance(p, goal) < distance(marker, goal) and not sealed(board, p, goal)
                ]
                row["options"] = len(destinations)
                if safe_closer:
                    row["alternative"] = safe_closer[0]
                dest = event["to"]
                row["choice"] = dest if dest is not None else "stay"
                if dest is None:
                    row["outcome"] = "elective_stay" if destinations else "forced_stay"
                elif not sealed(board, marker, goal) and sealed(board, tuple(dest), goal):
                    row["outcome"] = "enter_trap"
                elif tuple(dest) == goal:
                    row["outcome"] = "reach_exit"
                else:
                    row["outcome"] = "step"
        table.commit(event)
        if row:
            row["build_seals_marker"] = (
                stage == "place"
                and not previously_sealed
                and sealed(game.board, game.marker, game.goal)
            )
            yield row


def summarize(rows):
    counts = Counter()
    for r in rows:
        if r["timeout"]:
            counts["fallback"] += 1
            continue
        counts[r["outcome"]] += 1
        counts["build_seals_marker"] += r["build_seals_marker"]
        if r["outcome"] == "elective_stay" and r["alternative"] != "":
            counts["stay_with_closer"] += 1
    return counts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="game files or arm directories")
    parser.add_argument(
        "--events", action="store_true", help="include one seat-visible alternative per decision"
    )
    args = parser.parse_args()
    outcomes = [
        "used_build",
        "other_build",
        "no_build",
        "forced_stay",
        "elective_stay",
        "stay_with_closer",
        "step",
        "enter_trap",
        "build_seals_marker",
        "reach_exit",
        "fallback",
    ]
    writer = csv.writer(sys.stdout, lineterminator="\n")
    fields = [
        "arm",
        "game",
        "event",
        "turn",
        "stage",
        "timeout",
        "choice",
        "options",
        "alternative",
        "outcome",
        "build_seals_marker",
    ]
    writer.writerow(fields if args.events else ["arm", "games", *outcomes])
    for path in args.paths:
        files = sorted(path.glob("game-*.json")) if path.is_dir() else [path]
        if not files:
            parser.error(f"no games in {path}")
        rows = [r for f in files for r in decisions(f)]
        if args.events:
            for r in rows:
                writer.writerow(
                    [
                        json.dumps(r[k], separators=(",", ":"))
                        if isinstance(r[k], (list, tuple))
                        else r[k]
                        for k in fields
                    ]
                )
        else:
            c = summarize(rows)
            writer.writerow([files[0].parent.name, len(files), *(c[k] for k in outcomes)])
