"""Blind removal ballots whose two public continuations give opposite teams the last proposal."""

import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import product
from pathlib import Path
from random import Random

from experiments.skill_probe import MODEL
from experiments.voter_perspective import presentation
from footsteps.board import frontier, moves
from footsteps.decision_notes import open_private
from footsteps.ollama import decode_choice, request
from footsteps.record import replay
from footsteps.table import Table


def build(table, square):
    game = table.game
    n = min(len(game.store), 2)
    table.commit({"kind": "draw", "tiles": [255] * n})
    table.commit({"kind": "place", "at": list(square), "tile": 255, "rotation": 0})
    if game.stage == "discard":
        table.commit({"kind": "discard", "tile": 255})


def ballot(panel, nominee_team):
    turn, start, midpoint = {
        "east": (1, [-2, 0], [-1, 0]),
        "north": (2, [0, -2], [0, -1]),
        "wrap": (4, [2, 0], [1, 0]),
    }[panel]
    target, successor, observer = turn, (turn + 1) % 5, (turn + 2) % 5
    roles = ["blue"] * 5
    roles[observer] = "red"
    roles[target if nominee_team == "red" else successor] = "red"
    table = Table(
        {
            "roles": roles,
            "start": start,
            "goal": [0, 0],
            "hands": [[255] for _ in roles],
            "store": [255] * (turn + 1),
        },
        Random(98),
    )
    table.started = True
    build(table, midpoint)
    table.commit({"kind": "propose", "to": midpoint})
    table.commit({"kind": "move_vote", "votes": [True] * 5})
    for _ in range(1, turn):
        while table.game.stage == "nominate":
            table.commit({"kind": "nominate", "target": None})
        build(table, frontier(table.game.board, table.game.goal)[0])
        table.commit({"kind": "propose", "to": None})
    while table.game.queue[0] != table.game.actor:
        table.commit({"kind": "nominate", "target": None})
    table.commit({"kind": "nominate", "target": target})
    table.open_decision(0)
    return table, observer


def finish(table, seat, vote, controllers=None):
    branch = deepcopy(table)
    game = branch.game
    others = [s for s in game.alive if s != seat]
    yes = set(others[::2])
    branch.commit(
        {"kind": "eliminate_vote", "votes": [vote if s == seat else s in yes for s in game.alive]}
    )
    assert game.stage == "draw" and len(game.store) == 1
    final_builder = game.actor
    build(branch, frontier(game.board, game.goal)[0])
    assert game.goal in moves(game.board, game.marker)
    proposes_exit = (
        controllers[final_builder]
        if controllers is not None
        else game.roles[final_builder] == "blue"
    )
    step = list(game.goal) if proposes_exit else None
    branch.commit({"kind": "propose", "to": step})
    if step is not None:
        branch.commit(
            {
                "kind": "move_vote",
                "votes": [s == final_builder or game.roles[s] == "blue" for s in game.alive],
            }
        )
    assert game.winner and replay(branch.record).winner == game.winner
    return final_builder, game.winner, branch.record


def known_team(snap, seat):
    state = snap["state"]
    if seat == snap["seat"]:
        return state["role"]
    if state["role"] == "red":
        return "red" if seat in state["teammates"] else "blue"
    return "undisclosed"


def configure_response(body, arm):
    system = (
        "Cast your private decision for the public removal ballot. A strict majority of Yes removes the nominee. "
        "Blue wins if the shared marker enters EXIT. Red wins if it misses EXIT on the final turn or every Blue is removed. "
        "The final builder may stay or propose a connected step. If proposed, living seats vote, with a tie following the builder. "
        "Every player shares their team's result even after removal. "
        "vote is your own boolean ballot: true to remove the nominee, false to keep them. Give a short private reason."
    )
    vote_field = {"vote": {"type": "boolean"}}
    reason_field = {"reason": {"type": "string"}}
    fields = (
        {**vote_field, **reason_field}
        if arm in ("binary", "inline", "inline-team", "live-binary")
        else {**reason_field, **vote_field}
    )
    if arm == "forecast-first":
        system += (
            " Before voting, identify the final builder's team under each outcome, using your seat's knowledge. "
            "Use undisclosed when the team cannot be determined."
        )
        team_field = {"type": "string", "enum": ["blue", "red", "undisclosed"]}
        fields = {
            "team_building_if_removed": team_field,
            "team_building_if_kept": team_field,
            **fields,
        }
    if arm in ("silent", "ceiling"):
        system = system.removesuffix(" Give a short private reason.")
        fields = vote_field
    if arm == "live-binary":
        system = system.replace("The final builder", "The next builder")
    body["messages"][0]["content"] = system
    body["format"] = {
        "type": "object",
        "properties": fields,
        "required": list(fields),
        "additionalProperties": False,
    }


def prompt(snap, model, arm):
    relative = arm != "ordinary"
    body = presentation(snap, model, relative, relative, False, relative)
    if arm in ("ordinary", "relative"):
        return body
    state = snap["state"]
    cycle = [s for s in state["alive"] if s > state["actor"]] + [
        s for s in state["alive"] if s <= state["actor"]
    ]
    builders = {True: next(s for s in cycle if s != state["pending"]), False: cycle[0]}
    ctx = json.loads(body["messages"][1]["content"])
    if arm == "turn-order":
        ctx["next_builder_after_this_last_nomination"] = {
            "if_removed": f"P{builders[True]}",
            "if_kept": f"P{builders[False]}",
        }
    ctx["remaining_movement_opportunities"] = state["store_count"]
    ctx["legal_step_to_EXIT_already_on_floor"] = tuple(state["goal"]) in moves(
        dict(state["board"]), state["marker"]
    )
    if arm != "turn-order":
        del ctx["options"]
        votes = snap["choices"]["vote"]
        if arm in ("inline", "inline-team", "silent", "ceiling"):
            ctx["my_ballot_options"] = []
            for vote in votes:
                result = {
                    "my_vote": vote,
                    "if_pivotal": "remove nominee" if vote else "keep nominee",
                    "last_builder": f"P{builders[vote]}",
                }
                if arm != "inline":
                    result["last_builder_team_known_to_me"] = known_team(snap, builders[vote])
                ctx["my_ballot_options"].append(result)
        else:
            group_label = (
                "group_outcomes_if_no_further_removals_this_turn"
                if arm == "live-binary"
                else "group_outcomes"
            )
            builder_label = "next_builder" if arm == "live-binary" else "final_builder"
            if arm == "live-binary" and len(state["alive"]) <= state["red_count"] + 1:
                # Public counts permit a last-Blue removal. The survivor need not get a build.
                builder_label = "next_builder_if_play_continues"
            ctx[group_label] = {
                ("if_removed" if vote else "if_kept"): {
                    "nominee_remains_in_play": not vote,
                    builder_label: f"P{builders[vote]}",
                }
                for vote in votes
            }
        configure_response(body, arm)
    body["messages"][1]["content"] = json.dumps(ctx, separators=(",", ":"))
    return body


def disclose_programs(body, snap, controllers, arm):
    ctx = json.loads(body["messages"][1]["content"])
    ctx["public_experiment_setup"] = {
        "final_builder_programs": {
            f"P{s}": "proposes EXIT and votes Yes on its step" if steps else "stays"
            for s, steps in controllers.items()
        },
        "source": "These final-turn actions are fixed by the experiment and known to every seat.",
    }
    if arm in ("silent", "ceiling"):
        ctx["public_experiment_setup"]["other_final_movement_ballots"] = (
            "Blue votes Yes on EXIT and Red votes No."
        )
        if arm == "ceiling":
            # After either removal at least two Blues remain. On a tie the proposing builder approves.
            assert snap["state"]["red_count"] == 2 and len(snap["state"]["alive"]) == 5
            for effect in ctx["my_ballot_options"]:
                steps = controllers[int(effect["last_builder"][1:])]
                effect["winner_under_public_programs_if_pivotal"] = "blue" if steps else "red"
    body["messages"][1]["content"] = json.dumps(ctx, separators=(",", ":"))


def run(panel, arms, model, out, notes, controller=None, max_reply=144):
    for team in ("blue", "red"):
        table, observer = ballot(panel, team)
        controllers = None
        if controller:
            nominee = table.game.pending
            controllers = {
                nominee: controller == "nominee-steps",
                (nominee + 1) % 5: controller == "successor-steps",
            }
        for seat in (observer,) if controllers else (observer, table.game.pending):
            outcomes = {}
            for vote in (False, True):
                actor, winner, _ = finish(table, seat, vote, controllers)
                outcomes["remove" if vote else "keep"] = {"last_builder": actor, "winner": winner}
            assert outcomes["remove"]["winner"] != outcomes["keep"]["winner"]
            expected = outcomes["remove"]["winner"] == table.game.roles[seat]
            for arm, reverse in product(arms, (False, True)):
                snap = table.view(seat, table.opens)
                if reverse:
                    snap["choices"]["vote"] = list(reversed(snap["choices"]["vote"]))
                row = {
                    "panel": panel,
                    "model": model,
                    "seat": seat,
                    "self": seat == table.game.pending,
                    "nominee_team": team,
                    "arm": arm,
                    "reverse": reverse,
                    "outcomes": outcomes,
                    "expected_vote": expected,
                }
                body = prompt(snap, model, arm)
                body["options"]["num_predict"] = max_reply
                row["max_reply"] = max_reply
                if controllers:
                    row["controller"] = controller
                    disclose_programs(body, snap, controllers, arm)
                try:
                    reply = request(11434, "/api/chat", body, 30)
                    row.update(
                        prompt_tokens=reply.get("prompt_eval_count"),
                        reply_tokens=reply.get("eval_count"),
                    )
                    if reply.get("done_reason") == "length":
                        raise ValueError("reply cap")
                    if arm == "forecast-first":
                        answer = json.loads(reply["message"]["content"])
                        forecast = {
                            k: answer.pop("team_building_if_" + k) for k in ("removed", "kept")
                        }
                        row["forecast"] = forecast
                        reply = {**reply, "message": {"content": json.dumps(answer)}}
                    action, reason = decode_choice(
                        reply, body, snap["choices"], arm not in ("silent", "ceiling")
                    )
                    table_copy = deepcopy(table)
                    table_copy.submit(seat, table_copy.revision, action, table_copy.opens)
                    row.update(action)
                    assert table_copy.votes[seat] == row["vote"]
                    notes.write(json.dumps({**row, "reason": reason}) + "\n")
                    notes.flush()
                except (OSError, ValueError) as exc:
                    row["error"] = str(exc)
                out.write(json.dumps(row, separators=(",", ":")) + "\n")
                out.flush()


def summarize(path):
    counts = defaultdict(Counter)
    pairs = defaultdict(dict)
    for line in path.read_text().splitlines():
        r = json.loads(line)
        k = (r["panel"], r["arm"], "nominee" if r["self"] else "observer")
        c = counts[k]
        c["offered"] += 1
        hit = "vote" in r and r["vote"] == r["expected_vote"]
        c["aligned"] += hit
        c["accepted"] += "vote" in r
        if "controller" in r:
            pairs[k, (r["reverse"], r["nominee_team"])][r["controller"]] = hit
        else:
            pairs[k, r["reverse"]][r["nominee_team"]] = hit
    for k, c in counts.items():
        both = sum(
            all(pair.values()) and len(pair) == 2
            for (group, _), pair in pairs.items()
            if group == k
        )
        print(
            *k, dict(c), "complete correct pairs", both, "/", sum(group == k for group, _ in pairs)
        )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("--private", type=Path)
    cli.add_argument("--panel", choices=("east", "north", "wrap"))
    cli.add_argument(
        "--arms",
        nargs="+",
        choices=(
            "ordinary",
            "relative",
            "turn-order",
            "binary",
            "reason-first",
            "forecast-first",
            "inline",
            "inline-team",
            "silent",
            "ceiling",
        ),
    )
    cli.add_argument("--model", default=MODEL)
    cli.add_argument("--max-reply", type=int, choices=(144, 320), default=144)
    cli.add_argument(
        "--controllers",
        action="store_true",
        help="cross two public fixed final-builder policies for the observing seat",
    )
    a = cli.parse_args()
    if a.panel:
        if a.arms and "ceiling" in a.arms and not a.controllers:
            cli.error("ceiling requires public fixed controllers")
        if not a.private or not a.arms:
            cli.error("provide arms and a private notes path for model trials")
        with a.output.open("x") as out, open_private(a.private) as notes:
            for controller in ("nominee-steps", "successor-steps") if a.controllers else (None,):
                run(a.panel, a.arms, a.model, out, notes, controller, a.max_reply)
    else:
        summarize(a.output)
