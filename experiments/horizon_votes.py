"""Test four-seat outward steps with opposite, referee-verified consequences."""

import argparse
import json
from copy import deepcopy
from pathlib import Path
from random import Random

from experiments.game_efficiency import MODEL
from experiments.model_solitaire_audit import clockwise, rotate_event
from experiments.persistent_runtime import resident_model
from experiments.rana_speakers import SpeakerSeat, act
from footsteps.board import distance, optimistic_length
from footsteps.decision_notes import open_private
from footsteps.ollama import request
from footsteps.record import new_record, read, replay
from footsteps.session import Session
from footsteps.table import Table

ROOT = Path(__file__).parent
CONTEXT = 32768
BUDGET_RULE = (
    "Each build consumes one net tile from the store. At a movement ballot, store_count is the "
    "number of future movement opportunities after this ballot if play continues to depletion."
)
PRO_DETOUR = "I vote Yes. Stepping away now gives us a route back around toward EXIT. We have time for the detour."


def detour():
    setup = read(ROOT / "ballot-polling/four/game.json")["setup"]
    setup.update(start=[-3, 0], store=[136] + [255] * 9)
    record = new_record(setup)
    events = record["events"]
    path = [[-3, 1], [-2, 1], [-1, 1], [-1, 0], [0, 0]]
    destinations = [[-2, 0], None, None, None, [-3, 0], *path]
    placements = [[-2, 0], *path[:4]] + [[-3, -y] for y in range(1, 6)]
    for i, (at, to) in enumerate(zip(placements, destinations, strict=True)):
        face = 136 if i == 0 else 255
        draw = [face, 255] if i < 9 else [face]
        events.extend(
            [
                {"kind": "draw", "tiles": draw},
                {"kind": "place", "at": at, "tile": face, "rotation": 0},
            ]
        )
        if len(draw) == 2:
            events.append({"kind": "discard", "tile": 255})
        events.append({"kind": "propose", "to": to})
        if i == 4:
            revision = len(events)
        if to is not None:
            events.append({"kind": "move_vote", "votes": [True] * 4})
        if i < 9:
            events.extend({"kind": "nominate", "target": None} for _ in range(4))
    return record, revision


def fixture(case, heading):
    if case == "short":
        record, rev = read(ROOT / "ballot-polling/decline-west.json"), 4
        record.pop("remarks")
    else:
        record, rev = detour()
    if heading == "north":
        record["setup"]["start"] = clockwise(record["setup"]["start"])
        record["events"] = [rotate_event(e) for e in record["events"]]
    assert replay(record).winner == "blue"
    prefix = record | {"events": record["events"][:rev]}
    g = replay(prefix)
    assert g.actor == 0 and g.stage == "move_vote"
    assert distance(g.pending, g.goal) == 3 and distance(g.marker, g.goal) == 2
    # Give all unbuilt squares unrestricted connectivity. Even this bound rules
    # out Blue's alternative; the full referee witness certifies the other branch.
    losing = g.pending if case == "short" else g.marker
    assert optimistic_length(g.board, losing, g.goal, len(g.store)) is None
    winning_landing = g.pending if case == "detour" else g.marker
    g.apply(record["events"][rev])
    assert g.marker == winning_landing
    return prefix


class BudgetSession(Session):
    def reset(self, *, recovered=False):
        super().reset(recovered=recovered)
        self.messages[0]["content"] += " " + BUDGET_RULE


class CountedSession(BudgetSession):
    def opportunity(self):
        notice = super().opportunity()
        if notice["stage"] == "move_vote":
            notice["future_movement_opportunities_after_this_ballot"] = self.snap["state"][
                "store_count"
            ]
        return notice


def seat_session(prefix, seat, listener_team, remark=None, session_class=Session):
    setup = deepcopy(prefix["setup"])
    if listener_team == "red":
        setup["roles"][1], setup["roles"][3] = setup["roles"][3], setup["roles"][1]
    table = Table(setup, Random(128), seconds=45, discussion=30)
    for e in prefix["events"]:
        table.commit(e)
    peer = SpeakerSeat(table, seat)
    for i in range(4):
        table.join(i, 0)
    if remark:
        table.say(1, table.revision, remark, 0)
    if seat == 3:
        peer.now = table.opens
    return session_class(
        peer, sleep=peer.expire, inspect_rotations=True, movement_context=True, context=CONTEXT
    )


def question(messages, prompt, fields):
    schema = {
        "type": "object",
        "properties": {name: {"type": kind} for name, kind in fields.items()},
        "required": list(fields),
        "additionalProperties": False,
    }
    reply = request(
        11434,
        "/api/chat",
        {
            "model": MODEL,
            "stream": False,
            "think": False,
            "messages": [*messages, {"role": "user", "content": prompt}],
            "format": schema,
            "options": {"temperature": 0, "seed": 1, "num_ctx": CONTEXT, "num_predict": 256},
        },
        90,
    )
    try:
        answer = json.loads(reply["message"]["content"])
    except (KeyError, ValueError):
        return {}
    types = {"integer": int, "boolean": bool, "string": str}
    if not isinstance(answer, dict) or any(
        type(answer.get(k)) is not types[v] for k, v in fields.items()
    ):
        return {}
    return {k: answer[k] for k in fields}


def trial(prefix, listener_team, remark, key, owner):
    seat = key["seat"]
    session_class = {"budget_rule": BudgetSession, "budget_count": CountedSession}.get(
        key["condition"], Session
    )
    s = seat_session(prefix, seat, listener_team, remark, session_class)
    peer, calls = s.seat, []
    t = peer.table
    rev = t.revision
    if seat == 1:
        calls.extend(act(s, MODEL, True))
        peer.now = max(peer.now, t.opens)
    s.refresh()
    if t.revision == rev:
        calls.extend(act(s, MODEL, False))
    vote = t.votes.get(seat) if t.revision == rev else None
    public = next((r["text"] for r in t.record.get("remarks", []) if r["seat"] == seat), None)
    # Two separate post-choice forks. Neither answer can prime the other or affect the ballot.
    if t.revision != rev:
        return key | {"vote": None, "public_remark": public, "calls": calls, "facts": {}}
    messages = s.messages
    explanation = question(
        messages,
        "Privately explain your choice on the proposed step in one short sentence. What public evidence mattered to your team?",
        {"reason": "string"},
    )
    facts = question(
        messages,
        "Assess the proposal just voted on. Give the Manhattan distance from its proposed landing to EXIT and the number of future movement opportunities after this vote. For each ballot outcome, could Blue still reach EXIT with cooperative future play and favorable legal builds?",
        {
            "landing_distance": "integer",
            "future_moves": "integer",
            "possible_if_approved": "boolean",
            "possible_if_rejected": "boolean",
        },
    )
    print(json.dumps(key | explanation), file=owner, flush=True)
    return key | {"vote": vote, "public_remark": public, "calls": calls, "facts": facts}


def matched_listeners(prefix, position, listener_team, out, owner, aid):
    def save(seat, team, condition, remark=None):
        key = position | {"seat": seat, "team": team, "condition": condition}
        row = trial(prefix, listener_team, remark, key, owner)
        print(json.dumps(row), file=out, flush=True)
        return row["public_remark"]

    if aid:
        save(3, listener_team, aid)
        return
    speaker_team = "red" if listener_team == "blue" else "blue"
    speech = save(1, speaker_team, "speaker")
    for condition, remark in (("silent", None), ("scripted", PRO_DETOUR), ("model", speech)):
        save(3, listener_team, condition, remark)


def run(out, owner, aid):
    for case in ("short", "detour"):
        for heading in ("west", "north"):
            prefix = fixture(case, heading)
            for team in ("blue", "red"):
                matched_listeners(prefix, {"case": case, "heading": heading}, team, out, owner, aid)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("owner", type=Path)
    aid = cli.add_mutually_exclusive_group()
    aid.add_argument(
        "--budget-rule",
        dest="aid",
        action="store_const",
        const="budget_rule",
        help="repeat silent ballots with the depletion rule",
    )
    aid.add_argument(
        "--budget-count",
        dest="aid",
        action="store_const",
        const="budget_count",
        help="also give the literal future movement count on the ballot",
    )
    args = cli.parse_args()
    with args.output.open("x") as out, open_private(args.owner) as owner:
        run(out, owner, args.aid)
    print(json.dumps(resident_model(MODEL)))
