"""Optional social decision aids computed entirely from the requesting player's view."""

import json

from footsteps.board import distance
from footsteps.role_knowledge import role_information
from footsteps.social import TRUST, social_request, stated_votes
from footsteps.solo import sealed

STRATEGIES = (
    "baseline",
    "trust",
    "outcomes",
    "combined",
    "perspective",
    "perspective-trust",
    "payoff",
    "payoff-trust",
    "intent",
    "intent-trust",
    "human",
    "instrumental",
    "assisted",
)


def ballot_names(snap):
    state = snap["state"]
    seat, target = snap["seat"], state["pending"]
    if state["stage"] == "eliminate_vote":
        if seat == target:
            subject = f"myself_P{seat}"
        elif state["role"] == "red":
            known = "red_teammate" if target in state["teammates"] else "blue_player"
            subject = f"{known}_P{target}"
        else:
            subject = f"P{target}"
        return {True: f"remove_{subject}", False: f"keep_{subject}"}
    return {True: f"move_to_{target[0]}_{target[1]}", False: "remain_here"}


def outcomes(snap):
    state = snap["state"]
    seat, target = snap["seat"], state["pending"]
    names = ballot_names(snap)
    facts = {}
    for vote in (True, False):
        if state["stage"] == "move_vote":
            landing = tuple(target if vote else state["marker"])
            board = {tuple(p): f for p, f in state["board"]}
            gap = distance(landing, state["goal"])
            facts[names[vote]] = {
                "distance_after": gap,
                "turns_after": state["store_count"],
                "enter_EXIT_now": gap == 0,
                "EXIT_unreachable_even_with_perfect_future_tiles": gap > state["store_count"]
                or sealed(board, landing, tuple(state["goal"])),
            }
        else:
            alive = [s for s in state["alive"] if not vote or s != target]
            facts[names[vote]] = {
                "still_playing": [f"P{s}" for s in alive],
                "I_still_act": seat in alive,
            }
            if state["role"] == "red":
                red = {seat, *state["teammates"]}
                facts[names[vote]]["known_blue_still_playing"] = [
                    f"P{s}" for s in alive if s not in red
                ]
                facts[names[vote]]["red_wins_immediately"] = not any(s not in red for s in alive)
            elif state["player_count"] - state["red_count"] == 1:
                facts[names[vote]]["red_wins_immediately"] = seat not in alive
    return facts


def perspective(body, snap, trust):
    state = snap["state"]
    seat, role = snap["seat"], state["role"]
    objective = (
        "I win if time runs out or all Blue seats are eliminated. If the marker enters EXIT I lose."
        if role == "red"
        else "I win if the marker enters EXIT. If time runs out first or all Blue seats are removed I lose."
    )
    system = f"I am P{seat}, a {role.upper()} player. {objective} Removed players still share their team's result."
    if trust:
        system += " " + TRUST
    system += " Choose my action. Give one brief private reason from my own team's perspective."
    choices = json.loads(body["messages"][1]["content"])["options"]
    context = {
        "turn": state["turn"],
        **role_information(snap),
        "my_seat": f"P{seat}",
        "my_team": role,
        "initial_red_count": state["red_count"],
        "initial_player_count": state["player_count"],
        "living": [f"P{s}" for s in state["alive"]],
        "marker": state["marker"],
        "EXIT": state["goal"],
        "tiles_left": state["store_count"],
        "recent": [entry["text"] for entry in snap["history"][-12:]],
        "options": choices,
    }
    if role == "red":
        context["my_red_teammates"] = [f"P{s}" for s in state["teammates"]]
    stage = state["stage"]
    if stage == "nominate":
        context["decision"] = "Nominate a living player for removal, or pass."
    else:
        names = ballot_names(snap)
        effects = outcomes(snap)
        lines = {}
        for vote in (True, False):
            fact = effects[names[vote]]
            if stage == "move_vote":
                if fact["enter_EXIT_now"]:
                    effect = "Blue wins immediately."
                elif fact["EXIT_unreachable_even_with_perfect_future_tiles"]:
                    effect = "Blue cannot reach EXIT before depletion; Red is assured of winning."
                else:
                    effect = f"The marker is {fact['distance_after']} squares from EXIT with {fact['turns_after']} more moves."
            else:
                target = state["pending"]
                who = "I" if target == seat else f"P{target}"
                effect = (
                    f"{who} would lose all future builds, nominations, and votes."
                    if vote
                    else f"{who} would keep playing."
                )
                if fact.get("red_wins_immediately"):
                    effect += " The last Blue seat is gone. Red wins immediately."
            lines["approve" if vote else "reject"] = effect
        context["decision"] = (
            "Vote on moving to " + str(state["pending"])
            if stage == "move_vote"
            else f"Vote on removing P{state['pending']}"
            + (" (me)." if state["pending"] == seat else ".")
        )
        context["if_the_table_approves_or_rejects"] = lines
        context["ballot_rule"] = (
            "Movement ties follow the builder's vote."
            if stage == "move_vote"
            else "A strict majority is required for removal."
        )
        promises = stated_votes(snap)
        if len(promises) == len(state["alive"]) - 1:
            predicted = {}
            for vote in (True, False):
                votes = {**promises, seat: vote}
                yes = sum(votes.values())
                approved = 2 * yes > len(votes) or (
                    2 * yes == len(votes) and stage == "move_vote" and votes[state["actor"]]
                )
                predicted["approve" if vote else "reject"] = "approved" if approved else "rejected"
            context["result_if_others_vote_as_they_publicly_said"] = predicted
    body["messages"] = [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(context, separators=(",", ":"))},
    ]


def intentions(body, snap):
    """Let the model name a desired result, retaining a one-to-one map to legal commands."""
    key = next(iter(snap["choices"]))
    field = body["format"]["properties"][key]
    context = json.loads(body["messages"][1]["content"])
    actions = field["enum"]
    labels = []
    for action in actions:
        if "__MY_WIN" in action:
            name = "win"
        elif "__MY_LOSS" in action:
            name = "lose"
        else:
            name = action
        labels.append(name)
    names = [
        label if labels.count(label) == 1 else f"{label}_by_{action.split('__')[0]}"
        for label, action in zip(labels, actions, strict=True)
    ]
    context["options"] = dict(zip(names, actions, strict=True))
    field["enum"] = names
    if snap["state"]["role"] == "blue" and snap["state"]["stage"] in ("nominate", "eliminate_vote"):
        context["team_consideration"] = (
            "Removal costs a possible ally. Weigh public behavior and whether a useful builder would be lost. Passing is a legal decision."
        )
    body["messages"][0]["content"] += (
        " Select the name of the outcome you want. A win is your own team's win and a loss "
        "is your own team's loss. When the game is still open, judge which action gains "
        "time, trust or influence for you."
    )
    body["messages"][1]["content"] = json.dumps(context, separators=(",", ":"))


def apply_strategy(body, snap, strategy):
    if strategy not in STRATEGIES:
        raise ValueError("unknown social strategy")
    if strategy in ("human", "instrumental"):
        cue = (
            "Play like a person at the table. You want your team to win. While the outcome is open, "
            "you want to keep playing and do something that matters. If your team can win after "
            "you are out, take that over staying in a losing game."
            if strategy == "human"
            else "In this game, preserving your seat retains future builds and votes. Credibility preserves "
            "influence. These are useful only insofar as they serve the team's result. Spend them "
            "when doing so secures victory, including a posthumous victory."
        )
        body["messages"][0]["content"] += "\n" + TRUST + " " + cue
        return
    if strategy.startswith("intent"):
        social_request(body, snap, explain=True, trust=strategy == "intent-trust")
        intentions(body, snap)
        return
    if strategy.startswith("payoff"):
        social_request(body, snap, explain=True, trust=strategy == "payoff-trust")
        return
    if strategy.startswith("perspective"):
        perspective(body, snap, strategy == "perspective-trust")
        return
    system = body["messages"][0]
    if strategy in ("trust", "combined"):
        system["content"] += "\n" + TRUST
    if strategy in ("outcomes", "combined") and snap["state"]["stage"] in (
        "move_vote",
        "eliminate_vote",
    ):
        context = json.loads(body["messages"][1]["content"])
        names = ballot_names(snap)
        labels = [names[v == "approve"] for v in context["options"]["vote"]]
        context["options"]["vote"] = labels
        body["format"]["properties"]["vote"]["enum"] = labels
        context["majority_outcomes"] = outcomes(snap)
        system["content"] += (
            "\nReturn one exact action name in options.vote for the result you support. "
            "The vote is simultaneous. Your ballot may change the result or only what "
            "other seats learn about you. A removed seat shares its team's eventual result."
        )
        body["messages"][1]["content"] = json.dumps(context, separators=(",", ":"))
