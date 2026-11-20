"""Score a completed table's private placement attempts against its floor before each build."""

import argparse
import csv
import json
import sys
from pathlib import Path

from footsteps.board import connects, neighbors, rotate
from footsteps.game import integer, point
from footsteps.record import read, replay, starting_game


def subject(choice):
    """Identify the specific directed edge and rotated tile being judged."""
    if not isinstance(choice, dict):
        return None
    try:
        return point(choice["origin"]), point(choice["at"]), choice["tile"], choice["rotation"]
    except (KeyError, ValueError):
        return None


def first_answer(game, choice, mode):
    fields = {
        "edge_open": None,
        "first_edge_correct": None,
        "marker_on_origin": None,
        "first_marker_correct": None,
    }
    if (edge := subject(choice)) is None:
        return fields
    origin, dest, tile, rotation = edge
    if origin in game.board and origin != game.goal:
        fields["marker_on_origin"] = origin == game.marker
        if mode == "edge-and-marker" and type(choice.get("marker_on_origin")) is bool:
            fields["first_marker_correct"] = choice["marker_on_origin"] == (origin == game.marker)
        if (
            dest in neighbors(origin)
            and dest not in game.board
            and integer(tile)
            and tile in game.hands[game.actor]
            and integer(rotation)
            and 0 <= rotation < 4
        ):
            open_edge = connects(
                game.board[origin], rotate(tile, rotation), neighbors(origin).index(dest)
            )
            fields["edge_open"] = open_edge
            if type(choice.get("can_step")) is bool:
                fields["first_edge_correct"] = choice["can_step"] == open_edge
    return fields


def audit(record, logs):
    if not replay(record).winner:
        raise ValueError("use a completed game for postgame measurements")
    mode = record.get("placement_check")
    if mode not in ("edge", "edge-and-marker"):
        raise ValueError("record has no placement check")
    game = starting_game(record)
    logs = iter(logs)
    for event in record["events"]:
        if event["kind"] == "place":
            log = next(logs, {})
            fallback = event.get("timeout", False)
            if (
                log.get("turn") != game.turn
                or ("fallback" in log) != fallback
                or ("table_id" in log and log["table_id"] != record.get("table_id"))
            ):
                raise ValueError(f"attempt log does not match turn {game.turn} of this table")
            attempts = log["attempts"]
            if not fallback:
                actual = {k: event[k] for k in ("at", "tile", "rotation")}
                if (
                    not attempts
                    or attempts[-1][1] is not None
                    or any(attempts[-1][0].get(k) != v for k, v in actual.items())
                ):
                    raise ValueError(
                        f"accepted attempt differs from committed build on turn {game.turn}"
                    )
            first = attempts[0][0] if attempts else None
            retry = None
            if len(attempts) > 1:
                before, after = subject(first), subject(attempts[-1][0])
                if before and after:
                    retry = "same" if before == after else "changed"
                else:
                    retry = "unscorable"
            yield {
                "table_id": record.get("table_id"),
                "model": log.get("model"),
                "mode": mode,
                "turn": game.turn,
                "seat": game.actor,
                "team": game.roles[game.actor],
                **first_answer(game, first, mode),
                "attempts": len(attempts),
                "retry_subject": retry,
                "fallback": fallback,
            }
        game.apply(event)
    if next(logs, None) is not None:
        raise ValueError("unused placement attempt log entries")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--table",
        nargs=2,
        type=Path,
        action="append",
        required=True,
        metavar=("RECORD", "CHECKS_JSONL"),
    )
    args = parser.parse_args()
    writer = None
    for record, checks in args.table:
        with checks.open() as f:
            for row in audit(read(record), map(json.loads, f)):
                if writer is None:
                    writer = csv.DictWriter(sys.stdout, fieldnames=list(row), lineterminator="\n")
                    writer.writeheader()
                writer.writerow(row)


if __name__ == "__main__":
    main()
