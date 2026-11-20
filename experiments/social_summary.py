"""Replay the social panel and audit the committed social choices without opening private notes."""

import argparse
from collections import Counter
from pathlib import Path

from experiments.archive_rows import csv_rows, current_id
from footsteps.game import Game
from footsteps.record import read, replay


def game_totals(root):
    with (root / "choices.csv").open() as f:
        decisions = list(csv_rows(f))
    totals = Counter()
    for path in sorted(root.glob("*.json")):
        seed, red = current_id(path.stem).split("-red")
        record = read(path)
        winner = replay(record).winner
        assert winner in ("blue", "red")
        totals["games"] += 1
        totals["wins"] += winner == "blue"
        rows = [r for r in decisions if (r["seed"], r["red"]) == (seed, red)]
        observed = {(int(r["event"]), int(r.get("seat", 0))): r for r in rows}
        assert len(observed) == len(rows)
        debate = "seat" in rows[0]
        turns_out = []
        game = Game(record["setup"])
        for event, action in enumerate(record["events"], 1):
            stage = game.stage
            alive = game.alive.copy()
            if stage in ("nominate", "eliminate_vote"):
                voters = [game.queue[0]] if stage == "nominate" else alive
                for seat in voters:
                    if not debate and seat != 0:
                        continue
                    row = observed.pop((event, seat))
                    assert (row["stage"], int(row["turn"])) == (stage, game.turn)
                    if stage == "nominate":
                        target = action["target"]
                        assert row["choice"] == ("" if target is None else str(target))
                        if game.roles[seat] == "red":
                            totals["red nomination chances"] += 1
                            totals["red nominations"] += target is not None
                    else:
                        vote = action["votes"][alive.index(seat)]
                        assert row["choice"] == str(vote) and int(row["pending"]) == game.pending
                        if row.get("muted_vote") in ("True", "False"):
                            totals["matched listeners"] += 1
                            if row["muted_vote"] != row["choice"]:
                                totals["to yes" if vote else "to no"] += 1
            turn = game.turn
            game.apply(action)
            for lost in set(alive) - set(game.alive):
                totals[f"eliminated {game.roles[lost]}"] += 1
                turns_out.append(turn)
        totals["missed turns"] += sum(game.turn - t for t in turns_out)
        totals["remarks"] += len(record.get("remarks", []))
        assert not observed
    return totals


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=Path)
    root = cli.parse_args().root
    for panel in sorted(root.glob("*/choices.csv")):
        totals = game_totals(panel.parent)
        print(panel.parent.name, dict(totals))
    for path in sorted((root / "probes").glob("*.csv")):
        with path.open() as f:
            votes = [r for r in csv_rows(f) if r["target"]]
        totals = Counter()
        for row in votes:
            case = "voted no" if row["target"] == row["dissenter"] else "voted yes"
            totals[case] += 1
            totals[f"approved / {case}"] += row["choice"] == "True"
        print(path.stem, dict(totals))


if __name__ == "__main__":
    main()
