"""Frame public choices and provable consequences from one player's perspective."""

import json
import re

from .board import distance
from .decision_notes import REASON_PROMPT, request_reason
from .role_knowledge import role_information
from .solo import sealed

TRUST = (
    "Good players use behavior to infer loyalties the rules leave uncertain. A bad player who acts "
    "like a good player can earn trust and keep the freedom to act later. One helpful "
    "move or suspicious vote is evidence, and can have more than one explanation."
)
SOCIAL_STAGES = {"propose", "move_vote", "nominate", "eliminate_vote"}


def stated_votes(snap):
    """Collect explicit public forecasts in this window, without consulting the ballot box."""
    promises = {}
    for row in snap["history"]:
        if row["event"] != snap["revision"]:
            continue
        match = re.match(r"^P(\d+): I intend to vote (yes|no)\.", row["text"])
        if match:
            seat = int(match[1])
            if seat in snap["state"]["alive"] and seat != snap["seat"]:
                promises[seat] = match[2] == "yes"
    return promises


def forecast(snap):
    state = snap["state"]
    votes = stated_votes(snap)
    if len(votes) != len(state["alive"]) - 1:
        return None
    result = {}
    for name, value in (("yes", True), ("no", False)):
        votes[snap["seat"]] = value
        margin = 2 * sum(votes.values()) - len(votes)
        accepted = margin > 0 or (
            margin == 0 and state["stage"] == "move_vote" and votes[state["actor"]]
        )
        result[name] = "passes" if accepted else "fails"
    return result


def consequences(snap):
    state, me = snap["state"], snap["seat"]
    stage, role = state["stage"], state["role"]
    goal, marker = tuple(state["goal"]), tuple(state["marker"])
    board = {tuple(p): face for p, face in state["board"]}
    secret_bad = {me, *state.get("teammates", [])} if role == "bad" else set()
    options = next(iter(snap["choices"].values()))
    for value in options:
        winner = None
        immediate = False
        if stage in ("move_vote", "propose"):
            dest = (state["pending"] if value else None) if stage == "move_vote" else value
            at = marker if dest is None else tuple(dest)
            name = (
                ("yes_move" if value else "no_stay")
                if stage == "move_vote"
                else ("stay" if dest is None else f"propose_{at[0]}_{at[1]}")
            )
            if at == goal:
                winner = "good"
                immediate = True
            elif distance(at, goal) > state["store_count"] or sealed(board, at, goal):
                winner = "bad"
                immediate = state["store_count"] == 0
        elif stage == "eliminate_vote":
            target = state["pending"]
            subject = "myself" if target == me else f"P{target}"
            name = ("yes_remove_" if value else "no_keep_") + subject
            if value:
                survivors = set(state["alive"]) - {target}
                if (role == "bad" and survivors <= secret_bad) or (
                    target == me
                    and role == "good"
                    and state["player_count"] - state["bad_count"] == 1
                ):
                    winner = "bad"
                    immediate = True
        else:
            name = "pass" if value is None else f"nominate_P{value}"
        yield name, winner, immediate


def shortlist(snap):
    """Policy preference among legal options assuming they take effect."""
    key, options = next(iter(snap["choices"].items()))
    state = snap["state"]
    if state["stage"] not in ("move_vote", "propose", "eliminate_vote"):
        return options
    if key == "vote":
        prediction = forecast(snap)
        if prediction and prediction["yes"] == prediction["no"]:
            return options
    ranks = []
    for value, (_, winner, _) in zip(options, consequences(snap), strict=True):
        rank = 1 if winner is None else 2 if winner == state["role"] else 0
        if rank == 2 and key == "to" and value is None:
            rank = 3  # Staying executes immediately. Other proposals need the ballot.
        ranks.append(rank)
    best = max(ranks)
    return [value for value, rank in zip(options, ranks, strict=True) if rank == best]


def social_request(body, snap, *, explain, trust=True, human=False):
    state, me = snap["state"], snap["seat"]
    role = state["role"]
    goal = tuple(state["goal"])
    marker = tuple(state["marker"])
    objective = (
        "I win if the expedition runs out of tiles or eliminates every Good player. Entering EXIT makes me lose."
        if role == "bad"
        else "I win when the marker enters EXIT. Depletion or elimination of all Good players makes me lose."
    )
    system = f"You are P{me} on team {role.upper()}. Your private objective: {objective} Your team result counts even after removal."
    if trust:
        system += " " + TRUST
    system += " Choose an option for your own team's result. Weigh its effect if pivotal and the public impression it leaves."
    if human:
        system += " You want your team to win. While the result is open, stay in play and make a difference. A posthumous team win still counts."
        if state["stage"] == "nominate" and role == "good":
            system += " Pass without concrete public evidence against a particular player. You may need their next build."
    if explain:
        system += REASON_PROMPT
    stage = state["stage"]
    key = next(iter(snap["choices"]))
    names = []
    context = {
        **role_information(snap),
        "you": f"P{me}",
        "your_team": role,
        "stage": stage,
        "turn": state["turn"],
        "alive": state["alive"],
        "initial_bad_count": state["bad_count"],
        "initial_player_count": state["player_count"],
        "builder": state["actor"],
        "marker": marker,
        "EXIT": goal,
        "moves_after_this_turn": state["store_count"],
        "recent": snap["history"][-12:],
    }
    if role == "bad":
        context["known_bad_allies"] = state["teammates"]
    for name, winner, immediate in consequences(snap):
        if winner:
            payoff = "WIN" if winner == role else "LOSS"
            name += f"__MY_{payoff}" + ("_NOW" if immediate else "_ASSURED")
        names.append(name)
    if stage == "eliminate_vote":
        target = state["pending"]
        context["subject"] = f"P{target} (you)" if target == me else f"P{target}"
        context["vote_history"] = [
            e["text"] for e in snap["history"] if e["text"].startswith("Movement ballots — ")
        ][-6:]
    elif stage == "move_vote":
        context["proposed_square"] = state["pending"]
    if stage in ("eliminate_vote", "move_vote"):
        context["vote_rule"] = (
            "Strict majority; tied removal fails."
            if stage == "eliminate_vote"
            else "If tied, the builder's actual ballot decides."
        )
        estimate = forecast(snap)
        if estimate:
            context["if_other_seats_honor_their_stated_votes"] = estimate
    context["options"] = names
    context["reading_options"] = (
        "Team outcomes describe the result if that option takes effect. Other players can vote down a proposed move."
    )
    schema = {
        "type": "object",
        "properties": {key: {"type": "string", "enum": names}},
        "required": [key],
        "additionalProperties": False,
    }
    if explain:
        request_reason(schema)
    body["format"] = schema
    body["messages"] = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(context, separators=(",", ":"))},
    ]
