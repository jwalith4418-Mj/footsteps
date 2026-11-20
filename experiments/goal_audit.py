"""Replay the solitaire gate and quantify the social decisions' twelve-entry evidence window."""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from experiments.goal_pursuit import budget, choices_for, floor_report
from experiments.native_summary import game_results, rows
from footsteps.board import frontier, rotate
from footsteps.record import replay, starting_game


def history_window(record, decisions):
    # The host appends one history entry per adjudicated event to every seat and
    # one per public remark. Wording is seat-specific. The boundaries are shared.
    discussion = defaultdict(list)
    for r in record.get("remarks", []):
        discussion[r["after_event"]].append(r)
    by_revision = Counter((r["revision"], r["stage"]) for r in decisions)
    sequence = []
    stats = defaultdict(Counter)
    examples = {}
    for rev, e in enumerate(record["events"]):
        sequence.extend(("remark", r) for r in discussion[rev])
        stage = e["kind"]
        count = by_revision[rev, stage]
        if count:
            old = sequence[:-12]
            stats[stage]["decisions"] += count
            if old:
                stats[stage]["earlier_history_omitted"] += count
            old_remarks = [r for kind, r in old if kind == "remark"]
            if old_remarks:
                stats[stage]["prior_speech_omitted"] += count
                examples.setdefault(
                    stage, {"before_event": rev + 1, "first_omitted": old_remarks[0]}
                )
            if any(kind == "move_vote" for kind, _ in old):
                stats[stage]["prior_movement_ballot_omitted"] += count
        sequence.append((stage, e))
    return dict(stats), examples


def social_floor(record):
    """Use the builder's actual hand to distinguish actionable opportunities from a lost floor."""
    game = starting_game(record)
    result = {"good": Counter(), "bad": Counter()}
    ballots = []
    builds = []
    for index, e in enumerate(record["events"], 1):
        s = game.view(game.actor)
        board = dict(s["board"])
        marker, goal = game.marker, game.goal
        if e["kind"] == "place":
            options = {
                "tile": sorted(set(s["hand"])),
                "rotation": range(4),
                "at": frontier(board, goal),
            }
            all_builds = choices_for({"state": s, "choices": options})
            after = budget(s)
            board[tuple(e["at"])] = rotate(e["tile"], e["rotation"])
            chosen = floor_report(board, marker, goal, after)
            open_chosen = any(n is not None for _, n, _ in chosen)
            can_keep = any(any(n is not None for _, n, _ in report) for _, report in all_builds)
            can_cut = any(all(n is None for _, n, _ in report) for _, report in all_builds)
            team = s["role"]
            if can_keep and can_cut:
                result[team]["decisive_builds"] += 1
                result[team]["role_aligned_builds"] += (team == "good") == open_chosen
                builds.append([index, game.turn, game.actor, "preserved" if open_chosen else "cut"])
        elif e["kind"] == "move_vote":
            rows = choices_for({"state": s, "choices": {"vote": [True, False]}})

            def outcome(pair):
                n = pair[1][0][1]
                return 2 if n == 0 else int(n is not None)

            yes, no = map(outcome, rows)
            if yes != no:
                for seat, v in zip(game.alive, e["votes"], strict=True):
                    team = game.roles[seat]
                    result[team]["decisive_ballots"] += 1
                    result[team]["role_aligned_ballots"] += v is not None and v == (
                        (team == "good") == (yes > no)
                    )
                ballots.append([index, game.turn, yes, no, e["votes"]])
        game.apply(e)
    return {"teams": result, "builds": builds, "ballots": ballots}


def report(root):
    games = root / "games"
    totals = defaultdict(Counter)
    for p in sorted(games.glob("*.json")):
        record = json.loads(p.read_text())
        game = replay(record)
        group = p.stem.split("-")[-1]
        if p.stem.startswith("solo-"):
            totals[group]["games"] += 1
            totals[group]["wins"] += game.winner == "good"
        game_results(p)
        if len(game.roles) > 1:
            print("social floor", json.dumps(social_floor(record)))
            stats, examples = history_window(record, rows(p.with_suffix(".calls.jsonl")))
            print("history window", json.dumps(stats, sort_keys=True))
            if "nominate" in examples:
                print("first nomination with omitted remark", examples["nominate"])
    print("ordinary solitaire", json.dumps(totals, sort_keys=True))
    for p in sorted(root.glob("*.jsonl")):
        runs = rows(p)
        if not runs:
            continue
        if "attempts" in runs[0]:
            first = sum(
                bool(
                    r["attempts"]
                    and r["attempts"][0]["check"].get("possible_to_finish_from_proposed_landing")
                )
                for r in runs
            )
            print(
                p.stem,
                "initial/final viable",
                first,
                sum(r["viable"] for r in runs),
                "of",
                len(runs),
            )
        elif p.stem.startswith("ballots"):
            print(p.stem, [(r["case"], r.get("vote")) for r in runs])
        elif p.stem.startswith("social"):
            for i in range(0, len(runs), 2):
                if i + 1 < len(runs):
                    print(runs[i]["case"], "Blue/Red", runs[i]["success"], runs[i + 1]["success"])
        else:
            print(p.stem, sum(r["success"] for r in runs), "/", len(runs))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", nargs="?", type=Path, default=Path(__file__).with_name("goal-pursuit"))
    report(p.parse_args().root)
