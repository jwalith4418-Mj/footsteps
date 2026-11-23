"""Audit full-game outcomes, GPU service and a hypothetical per-seat reserve offline."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from footsteps.record import read, starting_game


def decisions(record):
    game = starting_game(record)
    for rev, event in enumerate(record["events"]):
        stage = event["kind"]
        if stage in ("move_vote", "eliminate_vote"):
            actions = zip(game.alive, (vote is None for vote in event["votes"]), strict=True)
        elif stage == "draw":
            actions = []
        else:
            seat = game.queue[0] if stage == "nominate" else game.actor
            actions = [(seat, bool(event.get("timeout")))]
        for seat, missed in actions:
            yield rev, game.turn, stage, seat, missed
        game.apply(event)
    assert game.winner


def service(row):
    return max(0, row["inference_seconds"] - row["queue_seconds"])


def reserve_audit(record, calls, base, cap, refill):
    banks = defaultdict(lambda: cap)
    last_turn = defaultdict(lambda: 1)
    for rev, turn, stage, seat, missed in decisions(record):
        bank = min(cap, banks[seat] + (turn - last_turn[seat]) * refill)
        last_turn[seat] = turn
        used = queued = 0
        warning = None
        tools = Counter()
        for row in calls[seat, rev]:
            notice = row.get("opportunity", {})
            if not notice.get("owe_action"):
                continue
            left = notice["seconds_left_in_phase"]
            queue = row["queue_seconds"]
            queued += min(left, queue)
            used += min(service(row), max(0, left - queue))
            tools[row["tool"]] += 1
            if warning is None and used > base:
                warning = max(0, left - row["inference_seconds"])
        banks[seat] = max(0, bank - max(0, used - base))
        yield {
            "rev": rev,
            "turn": turn,
            "stage": stage,
            "seat": seat,
            "missed": missed,
            "service": round(used, 2),
            "queue": round(queued, 2),
            "tools": dict(tools),
            "reserve_before": round(bank, 2),
            "reserve_after": round(banks[seat], 2),
            "wall_left_at_first_draw": None if warning is None else round(warning, 2),
            "over_budget": used > base + bank,
        }


def audit(root, base=15, cap=30, refill=3):
    record = read(root / "game.json")
    calls = defaultdict(list)
    costs = Counter()
    counts = Counter()
    for path in sorted(root.glob("seat-*.jsonl")):
        seat = int(path.stem.split("-")[1])
        for line in path.read_text().splitlines():
            row = json.loads(line)
            notice = row.get("opportunity", {})
            activity = "unclassified"
            if notice:
                activity = (
                    "decision"
                    if notice["owe_action"]
                    else ("discussion" if notice["can_speak"] else "background")
                )
            costs[activity] += service(row)
            costs["prefill"] += row.get("prefill_seconds", 0)
            costs["generation"] += row.get("generation_seconds", 0)
            counts[activity] += 1
            counts["errors"] += row["error"]
            counts["calls"] += 1
            calls[seat, row["revision"]].append(row)
            if row.get("num_predict") and row.get("reply_tokens") == row["num_predict"]:
                counts["at_token_cap"] += 1
                costs["at_token_cap"] += service(row)
    outcomes = list(reserve_audit(record, calls, base, cap, refill))
    timing = json.loads((root / "timing.json").read_text())
    elapsed = timing["play_seconds"]
    timely = sum(not o["missed"] for o in outcomes)
    windows = (
        {(o["seat"], o["rev"]) for o in outcomes if o["stage"] in ("move_vote", "eliminate_vote")}
        if timing["discussion_seconds"]
        else set()
    )
    speakers = {(r["seat"], r["after_event"]) for r in record.get("remarks", [])}
    tail_seconds = {}
    for rev in sorted({rev for _, rev in windows}):
        eligible = {seat for seat, r in windows if r == rev}
        if any((seat, rev) not in speakers for seat in eligible):
            continue
        remaining = [
            r["discussion"]["seconds_after_reply"]
            for seat in eligible
            for r in calls[seat, rev]
            if r["tool"] == "speak" and not r["error"] and r["discussion"]
        ]
        if len(remaining) == len(eligible):
            tail_seconds[rev] = min(remaining)
    game = starting_game(record)
    steps = 0
    for event in record["events"]:
        before = game.marker
        game.apply(event)
        steps += game.marker != before
    return {
        "game": root.name,
        "winner": game.winner,
        "turns": game.turn,
        "steps": steps,
        "speaking_windows": len(windows),
        "windows_with_remark": len(windows & speakers),
        "wall": elapsed,
        "timely": timely,
        "owed": len(outcomes),
        "timely_per_minute": round(timely * 60 / elapsed, 2),
        "remarks": len(record.get("remarks", [])),
        "discussion_left_at_last_reply": tail_seconds,
        "calls": dict(counts),
        "seconds": {k: round(v, 2) for k, v in costs.items()},
        "reserve_draws": sum(o["wall_left_at_first_draw"] is not None for o in outcomes),
        "over_budget": sum(o["over_budget"] for o in outcomes),
        "misses_or_draws": [
            o for o in outcomes if o["missed"] or o["wall_left_at_first_draw"] is not None
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("games", type=Path, nargs="+")
    parser.add_argument("--base", type=float, default=15)
    parser.add_argument("--cap", type=float, default=30)
    parser.add_argument("--refill", type=float, default=3)
    args = parser.parse_args()
    if min(args.base, args.cap, args.refill) < 0:
        parser.error("time allowances must be nonnegative")
    for root in args.games:
        print(json.dumps(audit(root, args.base, args.cap, args.refill), indent=2))
