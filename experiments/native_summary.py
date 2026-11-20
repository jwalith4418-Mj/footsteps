"""Tabulate paired decisions, accepted placements, and whole-game behavior from saved traces."""

import argparse
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path
from statistics import median

from experiments.archive_rows import json_rows as rows
from experiments.native_probe import panel
from experiments.native_transfer import transfer_panel
from experiments.rotation_probe import success
from footsteps.board import distance, moves
from footsteps.game import Game
from footsteps.record import read
from footsteps.solo import sealed


def probe_results(path):
    groups = defaultdict(list)
    for row in rows(path):
        panel = "ports" if row["case"].startswith("ports-") else "tactics"
        groups[row["arm"], panel].append(row)
    print(f"\n{path.stem}")
    print("arm panel | success / accepted / offered | orient / inspect / preview | median seconds")
    for (arm, panel), decisions in sorted(groups.items()):
        usage = Counter()
        for decision in decisions:
            usage.update({c["name"] for c in decision["calls"] if c["status"] == "ok"})
        print(
            arm,
            panel,
            "|",
            sum(r["success"] for r in decisions),
            "/",
            sum(r["status"] == "accepted" for r in decisions),
            "/",
            len(decisions),
            "|",
            usage["orient_tile"],
            "/",
            usage["inspect_rotations_at"],
            "/",
            usage["preview_placement"],
            "|",
            round(median(r["seconds"] for r in decisions), 2),
        )


def placement_diagnosis(paths):
    positions = {name: (snap, target) for name, snap, _, target in (*panel(), *transfer_panel())}
    groups = defaultdict(Counter)
    for path in paths:
        for row in rows(path):
            snap, target = positions[row["case"]]
            if target is not None:
                continue
            panel_name = "fresh" if row["case"].startswith("held-") else "archived"
            if path.stem == "isolated-square":
                panel_name = "isolated square"
            key = (panel_name, row["arm"])
            counts = groups[key]
            counts["offered"] += 1
            if row["success"]:
                counts[snap["state"]["role"]] += 1
                continue
            action = row["choice"]
            if not action:
                counts["missing"] += 1
                continue
            at = tuple(action["at"])
            faces = snap["choices"]["tile"]
            if any(success(snap["state"], action["tile"], rot, at, None) for rot in range(4)):
                counts["turn"] += 1
            elif any(
                success(snap["state"], face, rot, at, None)
                for face, rot in product(faces, range(4))
            ):
                counts["piece"] += 1
            else:
                counts["square"] += 1
    print(
        "\nTactical diagnosis | Blue hits / Red hits / turn same piece / change piece here / must change square / missing"
    )
    for key, c in sorted(groups.items()):
        print(
            *key,
            "|",
            " / ".join(str(c[k]) for k in ("blue", "red", "turn", "piece", "square", "missing")),
        )


def game_results(path):
    record = read(path)
    game = Game(record["setup"])
    decisions = rows(path.with_suffix(".calls.jsonl"))
    by_revision = defaultdict(list)
    for row in decisions:
        by_revision[row["revision"]].append(row)
    steps = rotations = 0
    first_trap = None
    eliminations = []
    nearest = distance(game.marker, game.goal)
    builds = []
    for index, event in enumerate(record["events"], 1):
        marker, alive, actor, turn = game.marker, set(game.alive), game.actor, game.turn
        stage = event["kind"]
        if stage == "draw":
            receipts = {}
        elif stage in ("move_vote", "eliminate_vote"):
            receipts = dict(zip(game.alive, [v is not None for v in event["votes"]], strict=True))
        else:
            seat = game.queue[0] if stage == "nominate" else actor
            receipts = {seat: not event.get("timeout", False)}
        actual = by_revision.pop(index - 1, [])
        assert all((row["turn"], row["stage"]) == (turn, stage) for row in actual)
        assert len(actual) == len(receipts)
        assert {row["seat"]: row["status"] == "accepted" for row in actual} == receipts
        game.apply(event)
        nearest = min(nearest, distance(game.marker, game.goal))
        steps += marker != game.marker
        if event["kind"] == "place":
            rotations += event["rotation"] != 0
            builds.append((turn, actor, bool(moves(game.board, game.marker))))
        if first_trap is None and sealed(game.board, game.marker, game.goal):
            first_trap = (turn, index)
        for seat in sorted(alive - set(game.alive)):
            eliminations.append((turn, seat))
    assert game.winner and not by_revision
    print(
        path.stem,
        game.winner,
        f"turn {game.turn}",
        f"ending {game.marker}",
        f"closest {nearest}",
        f"moves {steps}",
        f"builds with an available step {sum(b[2] for b in builds)}/{len(builds)}",
        f"nonzero rotations {rotations}",
        f"first trap (turn,event) {first_trap}",
        f"eliminations (turn,seat) {eliminations}",
    )
    for stage in dict.fromkeys(r["stage"] for r in decisions):
        stage_rows = [r for r in decisions if r["stage"] == stage]
        print(" ", stage, sum(r["status"] == "accepted" for r in stage_rows), "/", len(stage_rows))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "directory", type=Path, nargs="?", default=Path(__file__).with_name("native-actions")
    )
    root = p.parse_args().directory
    opening = root / "openings.jsonl"
    if opening.exists():
        groups = defaultdict(list)
        for row in rows(opening):
            groups[row["arm"]].append(row)
        print("Opening | one advertised call / replies | median seconds")
        for arm, trials in sorted(groups.items()):
            names = {"place_tile", "preview_placement", "orient_tile"}
            count = sum(len(r.get("names", [])) == 1 and r["names"][0] in names for r in trials)
            print(arm, count, "/", len(trials), "|", round(median(r["seconds"] for r in trials), 2))
    paths = sorted(p for p in root.glob("*.jsonl") if p != opening)
    for path in paths:
        probe_results(path)
    placement_diagnosis(paths)
    for path in sorted((root / "games").glob("*.json")):
        game_results(path)
