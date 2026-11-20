"""Experimental seat adapter for nominations and elimination ballots."""

import json
import re

from experiments.behavior_context import apply_strategy
from footsteps.board import distance
from footsteps.decision_notes import save_note
from footsteps.ollama import model_request, request
from footsteps.role_knowledge import role_information
from footsteps.team_names import color_brief


def progress_ballots(snap):
    """Recover direction and named votes from complete published referee sentences."""
    marker = (0, 0)
    rows = []
    goal = snap["state"]["goal"]
    proposal = None
    for entry in snap["history"]:
        text = entry["text"]
        move = re.fullmatch(r"P(\d+) proposed moving to \((-?\d+), (-?\d+)\)\.", text)
        if move:
            actor, x, y = map(int, move.groups())
            proposal = {
                "builder": f"P{actor}",
                "from_distance": distance(marker, goal),
                "to_distance": distance((x, y), goal),
            }
        ballot = re.fullmatch(r"Movement ballots — (.+)\. Marker at \((-?\d+), (-?\d+)\)\.", text)
        if ballot:
            votes, x, y = ballot.groups()
            if proposal is None:
                raise ValueError("movement ballot without a proposal")
            rows.append(
                {
                    "turn": entry["turn"],
                    **proposal,
                    "votes": dict(v.split(" ", 1) for v in votes.split(", ")),
                }
            )
            marker = (int(x), int(y))
            proposal = None
    return rows


def social_choice(snap, model, arm, sink, *, reverse=False, bad_brief=False, strategy="baseline"):
    stage = snap["state"]["stage"]
    body = model_request(snap, model, guided=True, named_ballots=True, explain=True)
    body["think"] = False
    key = "vote" if stage == "eliminate_vote" else "target"
    options = list(snap["choices"][key])
    if reverse:
        options.reverse()
    context = json.loads(body["messages"][1]["content"])
    schema = body["format"]["properties"]
    if key == "vote":
        labels = ["approve" if v else "reject" for v in options]
    elif arm != "base":
        labels = ["pass" if v is None else f"P{v}" for v in options]
    else:
        labels = list(range(len(options)))
    schema[key] = {"type": "integer" if isinstance(labels[0], int) else "string", "enum": labels}
    context["options"] = {key: options if isinstance(labels[0], int) else labels}
    if arm != "base":
        alive = ", ".join(f"P{i}" for i in snap["state"]["alive"])
        target = snap["state"]["pending"]
        decision = (
            f"P{target} has been nominated. Approve removes P{target} if a majority agrees; "
            f"reject keeps P{target} in play if the nomination fails."
            if key == "vote"
            else "Name a living opponent to put their elimination to a vote, or pass."
        )
        body["messages"][0]["content"] += (
            f"\nThis is an elimination decision. You are P{snap['seat']}. Living seats: {alive}. "
            f"{decision} The marker stays in place either way. Use the action names in options. "
            "Use your private role information and the table's public behavior. "
            "Explain your judgment about the player, or why you pass."
        )
    if arm in ("ledger", "receipt"):
        context["published_movement_ballots"] = progress_ballots(snap)
        body["messages"][0]["content"] += (
            " Check the published movement ballots before attributing a vote. Distance counts squares to EXIT. "
            "A player's accusation or nomination is a claim, not proof. If good, weigh evidence for and "
            "against removing this particular player; with insufficient evidence you can pass or reject. "
            "Bad may benefit from removing good seats."
        )
    if arm == "receipt" and key == "vote":
        nominee = f"P{snap['state']['pending']}"
        receipts = [
            f"Turn {row['turn']}: {nominee} voted {row['votes'][nominee]} on a move from "
            f"{row['from_distance']} to {row['to_distance']} squares from EXIT."
            for row in context["published_movement_ballots"]
            if nominee in row["votes"]
        ]
        context["nominee_voting_record"] = receipts
    if bad_brief and snap["state"]["role"] == "bad" and snap["state"]["bad_count"] == 1:
        others = [f"P{i}" for i in snap["state"]["alive"] if i != snap["seat"]]
        context["private_role_card"] = (
            f"You are P{snap['seat']}, the only Bad player. The other living players "
            f"({', '.join(others)}) are all Good. You win if they are all eliminated or "
            "if the marker misses EXIT before time expires. Judge this choice for Bad."
        )
    body["messages"][1]["content"] = json.dumps(context, separators=(",", ":"))
    apply_strategy(body, {**snap, "choices": {key: options}}, strategy)
    labels = body["format"]["properties"][key]["enum"]
    reply = json.loads(request(11434, "/api/chat", body, 30)["message"]["content"])
    chosen = {key: options[labels.index(reply[key])]}
    save_note(sink, snap, model, chosen, reply["reason"], [])
    return chosen


def advocate(snap, model, *, audience=False):
    """Write a deliberately public statement, independently of any private note."""
    state = snap["state"]
    body = {
        "model": model,
        "think": False,
        "stream": False,
        "format": {
            "type": "object",
            "properties": {"statement": {"type": "string", "maxLength": 240}},
            "required": ["statement"],
            "additionalProperties": False,
        },
        "options": {"temperature": 0, "seed": 1, "num_ctx": 4096, "num_predict": 100},
        "messages": [
            {
                "role": "system",
                "content": "You nominated another player in Footsteps. Good wants the marker to reach EXIT. Bad wants time to run out or all good seats eliminated. Address the other players in one short public sentence to persuade them to remove your nominee. You may stay silent with an empty string. Use the public floor or ballots to make your case. Keep your role and hand private.",
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        **role_information(snap),
                        "initial_seats": state["player_count"],
                        "initial_bad": state["bad_count"],
                        "you": snap["seat"],
                        "your_role": state["role"],
                        "alive": state["alive"],
                        "nominee": state["pending"],
                        "turn": state["turn"],
                        "ballots": progress_ballots(snap),
                        "recent": [h["text"] for h in snap["history"][-12:]],
                    }
                ),
            },
        ],
    }
    if audience:
        body["messages"][0]["content"] += (
            " Consider what listeners on the other team would infer about your allegiance and "
            "why they would support your proposal. If you lack a credible public case, you can stay silent."
        )
    if snap.get("team_names") == "colors":
        color_brief(body)
    reply = json.loads(request(11434, "/api/chat", body, 30)["message"]["content"])
    return reply["statement"].strip()
