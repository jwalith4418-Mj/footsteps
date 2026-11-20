"""Matched solitaire and social floor decisions from a single seat's projection."""

import argparse
import json
import secrets
from pathlib import Path
from random import Random
from time import monotonic

from experiments.native_games import play
from experiments.skill_probe import MODEL
from experiments.social_evidence import social_deal
from footsteps.action_tools import native_decision
from footsteps.board import distance, moves, neighbors, optimistic_length, rotate
from footsteps.decision_notes import save_note
from footsteps.game import with_exit_origin
from footsteps.ollama import request
from footsteps.seat_tools import rotations_of
from footsteps.solo import sealed, setup
from footsteps.table import Table, fixed_kit

HEADINGS = {"east": (2, 0), "north": (0, 2), "west": (-2, 0), "south": (0, -2)}


def budget(state):
    return state["store_count"] + int(state["stage"] == "place" and state["draw_count"] == 2)


def worksheet(snap):
    s = snap["state"]
    marker, goal = tuple(s["marker"]), tuple(s["goal"])
    after = budget(s)
    return {
        "actual_marker": marker,
        "EXIT": goal,
        "proposals_left_including_this_one": after + 1,
        "proposals_after_this_one": after,
        "hypothetical_landings": [
            {
                "at": p,
                "distance_after": distance(p, goal),
                "within_distance_budget": distance(p, goal) <= after,
            }
            for p in (marker, *neighbors(marker))
        ],
        "private_turns": [rotations_of(f) for f in dict.fromkeys(s["hand"])],
        "instruction": "Choose a first landing for your team. Check whether you can still reach EXIT in time from there, then check both directed edges. A distance within budget can still be blocked. A build never moves the marker.",
    }


def floor_report(board, marker, goal, after):
    """A row describes the result if the table stays or agrees to one of the steps."""
    return tuple(
        (p, optimistic_length(board, p, goal, after), sealed(board, p, goal))
        for p in (marker, *moves(board, marker))
    )


def choices_for(snap):
    s, opts = snap["state"], snap["choices"]
    board = {tuple(p): f for p, f in s["board"]}
    marker, goal = tuple(s["marker"]), tuple(s["goal"])
    after = budget(s)
    if s["stage"] == "place":
        groups = {}
        for at in map(tuple, opts["at"]):
            for face in opts["tile"]:
                for rot in opts["rotation"]:
                    board[at] = rotate(face, rot)
                    signature = floor_report(board, marker, goal, after)
                    groups.setdefault(signature, {"at": list(at), "tile": face, "rotation": rot})
            del board[at]
        return [(action, report) for report, action in groups.items()]
    if s["stage"] == "propose":
        actions = [({"to": p}, marker if p is None else tuple(p)) for p in opts["to"]]
    else:
        actions = [({"vote": v}, tuple(s["pending"]) if v else marker) for v in opts["vote"]]
    return [
        (a, ((p, optimistic_length(board, p, goal, after), sealed(board, p, goal)),))
        for a, p in actions
    ]


def card(report):
    return [
        [list(p), "EXIT" if n == 0 else "sealed" if trap else "out of time" if n is None else n]
        for p, n, trap in report
    ]


def plain_forecast(report):
    viable = [(n, p) for p, n, _ in report if n is not None]
    if not viable:
        if all(trap for _, _, trap in report):
            return "Every landing permanently seals the marker away from EXIT."
        return "No landing can reach EXIT in time, even with perfect future tiles."
    steps, landing = min(viable)
    if steps == 0:
        return f"Landing at {landing} reaches EXIT now."
    return f"Landing at {landing} leaves a possible route to EXIT in {steps} further steps."


def decide(snap, model, notes, log, *, arm, order, max_reply=140):
    start = monotonic()
    s = snap["state"]
    if arm == "ledger":
        # Submit an explicit rotation in one call. No host-side orientation mutation is needed.
        return native_decision(
            snap,
            model,
            30,
            mode="direct",
            trace=log,
            note_file=notes,
            task=json.dumps(worksheet(snap)),
        )
    choices = choices_for(snap)
    order.shuffle(choices)
    names = {f"P{i + 1}": pair for i, pair in enumerate(choices)}
    if arm == "uniform":
        pick = order.choice(list(names))
        reason = "Uniform among displayed outcomes."
    else:
        stage = s["stage"]
        custom = stage == "place"
        options = list(names) + (["custom"] if custom else [])
        schema = {
            "type": "object",
            "properties": {
                "choice": {"type": "string", "enum": options},
                "reason": {"type": "string"},
            },
            "required": ["choice", "reason"],
        }
        if arm == "last":
            # Keep the same fields and wording; only their generation order differs.
            schema["properties"] = {
                "reason": schema["properties"]["reason"],
                "choice": schema["properties"]["choice"],
            }
            schema["required"] = ["reason", "choice"]
        if custom:
            schema["properties"].update(
                {k: {"type": "integer"} for k in ("x", "y", "tile", "rotation")}
            )
        ctx = {
            "team": "Blue" if s["role"] == "good" else "Red",
            "seat": snap["seat"],
            "living": s["alive"],
            "proposer": s["actor"],
            "pending_step": s["pending"],
            "initial_red_count": s["bad_count"],
            "floor": s["board"],
            "known_allies": s.get("teammates", []),
            "stage": stage,
            "marker": s["marker"],
            "EXIT": s["goal"],
            "further_steps": budget(s),
            "recent_public_and_own_history": [e["text"] for e in snap["history"][-12:]],
            "candidates": {k: [a, card(r)] for k, (a, r) in names.items()},
        }
        if arm in ("brief", "personal", "last"):
            ctx["candidates"] = {
                k: {"action": a, "floor_result": plain_forecast(r), "landings": card(r)}
                for k, (a, r) in names.items()
            }
        if custom:
            ctx.update(hand=s["hand"], empty=snap["choices"]["at"])
        system = (
            "You play Footsteps. Blue wants EXIT before time expires. Red wants the marker to miss EXIT or every Blue removed. "
            "Everyone knows that Red knows all Red seats and Blue knows only its own role. Public claims can be false. A tied movement ballot follows the proposer. Choose for your private team. A build leaves the marker in place. The group may stay or approve a one-square step. "
            "For each action the referee calculated [landing, fewest further steps to EXIT on an optimistic floor]. "
            "The bound assumes perfectly connected future tiles. A number is possible, never guaranteed. "
            "'out of time' rules out reaching EXIT in time, 'sealed' is permanently confined. "
            "During placement the FIRST landing is stay and the rest are all possible steps. "
            "For a movement ballot compare where acceptance and rejection leave the team. "
            "Give a candidate name and a brief private reason. To make another legal build use custom and literal tile, rotation, x, y."
        )
        if arm in ("brief", "personal", "last"):
            system += (
                " Consider the floor_result for every candidate. Blue seeks an immediate EXIT or the shortest still-possible route. "
                "Red can obstruct everyone if every landing is sealed or out of time. Choose for your team even when the hopeful step is farther away."
            )
        if arm == "personal":
            system = (
                "Your private team is RED. You win if Blue cannot reach EXIT in time. "
                if s["role"] == "bad"
                else "Your private team is BLUE. You win if the marker reaches EXIT in time. "
            ) + system
        body = {
            "model": model,
            "stream": False,
            "think": False,
            "format": schema,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(ctx, separators=(",", ":"))},
            ],
            "options": {"temperature": 0, "seed": 1, "num_ctx": 4096, "num_predict": max_reply},
        }
        left = 30 - (monotonic() - start)
        if left <= 0:
            raise TimeoutError("forecast deadline")
        response = request(11434, "/api/chat", body, left)
        log.append(
            {
                "name": "inference",
                "prompt_tokens": response.get("prompt_eval_count"),
                "reply_tokens": response.get("eval_count"),
                "done_reason": response.get("done_reason"),
            }
        )
        if (
            response.get("done_reason") == "length"
            or response.get("prompt_eval_count", 0) >= 4096 - max_reply
        ):
            raise ValueError("forecast context or reply at limit")
        ans = json.loads(response["message"]["content"])
        if not isinstance(ans, dict) or ans.get("choice") not in options:
            raise ValueError("missing or unknown forecast choice")
        log[-1]["response_fields"] = list(ans)
        pick, reason = ans["choice"], ans.get("reason")
        if pick == "custom":
            action = {
                "tile": ans.get("tile"),
                "rotation": ans.get("rotation"),
                "at": [ans.get("x"), ans.get("y")],
            }
            if not (
                type(action["tile"]) is int
                and action["tile"] in s["hand"]
                and type(action["rotation"]) is int
                and action["rotation"] in range(4)
                and all(type(v) is int for v in action["at"])
                and tuple(action["at"]) in map(tuple, snap["choices"]["at"])
            ):
                raise ValueError("invalid custom placement")
    if pick != "custom":
        action = names[pick][0]
    if monotonic() - start >= 30:
        raise TimeoutError("forecast deadline")
    log.append(
        {
            "name": "floor_forecast",
            "status": "commit",
            "candidates": {k: [a, card(r)] for k, (a, r) in names.items()},
            "selected": pick,
        }
    )
    if notes is not None:
        save_note(notes, snap, model, action, reason, [])
    return action


def run(root, private, case, seed, arm, model, *, max_reply=140):
    key = f"{case}-{seed}-{arm}"
    if max_reply != 140:
        key += f"-r{max_reply}"
    if case in HEADINGS:
        initial = {"roles": ["good"], "goal": HEADINGS[case], "hands": [[65]], "store": [65, 65]}
    elif case == "solo":
        initial = setup(seed, (3, 2), 2, 7, 0.55)
    else:
        roles = (
            ["good", "bad", "good", "good"]
            if case == "four"
            else ["good", "bad", "good", "bad", "good"]
        )
        initial = social_deal(seed, roles, fixed_kit(Random(8700), 16, 29, 29))
        initial["goal"] = [2, 2]
    t = Table(with_exit_origin(initial), Random(f"draw/{seed}"), discussion=1, color_teams=True)
    t.record["table_id"] = secrets.token_hex(16)
    for seat in range(len(t.game.roles)):
        t.join(seat, 0)
    rng = Random(f"display/{seed}")

    def policy(snap, model, notes, log):
        return decide(snap, model, notes, log, arm=arm, order=rng, max_reply=max_reply)

    play(
        t,
        key,
        root,
        private,
        model,
        "hand" if arm == "baseline" else arm,
        "build",
        floor_policy=None if arm == "baseline" else policy,
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("root", type=Path)
    p.add_argument("private", type=Path)
    p.add_argument("--cases", nargs="+", choices=[*HEADINGS, "solo", "four", "five"], required=True)
    p.add_argument(
        "--arms",
        nargs="+",
        choices=["baseline", "ledger", "forecast", "brief", "personal", "last", "uniform"],
        required=True,
    )
    p.add_argument("--seeds", nargs="+", type=int, default=[9501])
    p.add_argument("--model", default=MODEL)
    p.add_argument("--max-reply", type=int, choices=(140, 320), default=140)
    args = p.parse_args()
    args.root.mkdir(parents=True, exist_ok=True)
    args.private.mkdir(parents=True, exist_ok=True)
    for seed in args.seeds:
        for case in args.cases:
            for arm in args.arms:
                run(args.root, args.private, case, seed, arm, args.model, max_reply=args.max_reply)
