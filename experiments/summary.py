"""Summarize pilot.csv by configuration, remaining time, and paired prefix."""

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

from footsteps.solo import POLICIES


def summarize(rows):
    groups = defaultdict(list)
    finishes = defaultdict(Counter)
    pairs = defaultdict(dict)
    for r in rows:
        key = (int(r["goal_x"]), int(r["goal_y"]), int(r["store"]), int(r["hand"]))
        win = int(r["win"])
        policy = r["policy"]
        groups[key, policy].append(win)
        if key[2] == 10:
            finish = r["turns"] if win else "loss"
            finishes[policy][finish] += 1
            finishes[policy]["sealed"] += int(r["sealed"])
        if policy in ("greedy", "switch"):
            pairs[key, r["seed"]][policy] = (r["near_turn"], win)

    print("| Goal | Store after deal | Hand | Games per policy | " + " | ".join(POLICIES) + " |")
    print("|---|---:|---:|---:|" + "---:|" * len(POLICIES))
    for key in sorted({k for k, _ in groups}):
        x, y, store, hand = key
        wins = " | ".join(str(sum(groups[key, p])) for p in POLICIES)
        print(f"| ({x}, {y}) | {store} | {hand} | {len(groups[key, 'greedy'])} | {wins} |")
    print("\nTen-turn games, pooled across goal shape and hand size. Counts by finish turn.\n")
    print("| Policy | 6 | 7 | 8 | 9 | 10 | Loss | Of losses, certified trapped |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for p in POLICIES:
        counts = [finishes[p][k] for k in ("6", "7", "8", "9", "10", "loss", "sealed")]
        print(f"| {p} | " + " | ".join(map(str, counts)) + " |")

    reached = Counter()
    for pair in pairs.values():
        when, baseline = pair["greedy"]
        fork, alternate = pair["switch"]
        if fork != when:
            raise ValueError("unmatched prefix")
        if when:
            reached[baseline, alternate] += 1
    print(
        f"\nOf {len(pairs)} paired starts, {reached.total()} reached the switch point. "
        f"Both won {reached[1, 1]}, only switch won {reached[0, 1]}, "
        f"only greedy won {reached[1, 0]}, and both lost {reached[0, 0]}."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, nargs="?", default=Path("experiments/pilot.csv"))
    with parser.parse_args().path.open() as f:
        summarize(csv.DictReader(f))
