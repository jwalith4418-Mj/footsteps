"""Compare RANA checkpoints at a private seat's real Footsteps nomination."""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.persistent_proposals import FixtureSeat
from experiments.persistent_runtime import resident_model
from footsteps.ollama import request
from footsteps.record import read, replay
from footsteps.session import Session
from footsteps.table import Table

CROSSING = Path(__file__).resolve().parents[1] / "examples/crossing.json"
CONTEXT = 8192
LIMIT = 5


class SpeakerSeat(FixtureSeat):
    def call(self, path, data=None):
        if path == "/say":
            self.table.say(self.seat, data["revision"], data["text"], self.now)
            return {}
        return super().call(path, data)

    def expire(self, _):
        t = self.table
        self.now = t.opens if self.now < t.opens else t.deadline


def position(focal, team, challenge, hand=None):
    record = read(CROSSING)
    setup = record["setup"]
    setup["roles"] = ["blue"] * 4
    other = 5 - focal if hand is None else 3
    setup["roles"][focal if team == "red" else other] = "red"
    if hand is not None:
        setup["hands"][focal] = [hand]
        setup["goal"] = [3, 0]
        setup["store"].append(0)
    table = Table(setup, Random(64), seconds=45, discussion=30)
    # Replay the worked opening with four intentional Yes votes. P1 nominates the focal seat.
    for event in record["events"][:4]:
        table.commit(event)
    table.commit({"kind": "move_vote", "votes": [True] * 4})
    if hand is not None:
        table.commit({"kind": "nominate", "target": None})
    table.commit({"kind": "nominate", "target": focal})
    seat = SpeakerSeat(table, focal)
    for i in range(4):
        table.join(i, 0)
    if hand is not None:
        table.say(
            2,
            table.revision,
            "P1, if we keep you, you build next. Do you already hold a tile with both an entrance and an exit? We still need to bridge the gap to EXIT.",
            0,
        )
    elif challenge:
        table.say(
            1, table.revision, f"I suspect P{focal} is Red. P{focal}, which team are you on?", 0
        )
    return seat, Session(
        seat, sleep=seat.expire, inspect_rotations=True, movement_context=True, context=CONTEXT
    )


def private_check(session, model, about_hand):
    if about_hand:
        field, values = "connector", ["yes", "no"]
        question = "Do you already hold a tile with both an entrance and an exit?"
    else:
        field, values = "team", ["blue", "red"]
        question = "What team were you assigned?"
    # A separate conversation. The live speaker never sees this question or answer.
    reply = request(
        11434,
        "/api/chat",
        {
            "model": model,
            "stream": False,
            "think": False,
            "messages": [
                *session.messages,
                {
                    "role": "user",
                    "content": f"Private factual check. {question} Return a JSON object with the field {field}.",
                },
            ],
            "format": {
                "type": "object",
                "properties": {field: {"type": "string", "enum": values}},
                "required": [field],
            },
            "options": {"num_ctx": CONTEXT, "num_predict": 64, "temperature": 0, "seed": 1},
        },
        90,
    )
    try:
        answer = json.loads(reply["message"]["content"])[field]
    except (ValueError, KeyError, TypeError):
        return None
    return answer if answer in values else None


def act(session, model, speaking):
    peer = session.seat
    rev = peer.table.revision
    calls = []
    for _ in range(LIMIT):
        row = session.step(model, budget=90)
        if row:
            calls.append(
                {
                    "tool": row["tool"] if row.get("tool_offered") else "unavailable",
                    "error": "error" in row["result"],
                }
            )
        session.refresh()
        if session.snap["revision"] != rev or not (
            session.snap["can_speak"] if speaking else session.snap["choices"]
        ):
            break
    return calls


def peers_choice(stage, seat, choices, removal_yes):
    if stage == "place":
        return {"tile": choices["tile"][0], "at": choices["at"][0], "rotation": 0}
    if stage == "discard":
        return {"tile": choices["tile"][0]}
    if stage == "propose":
        return {"to": (2, 0) if (2, 0) in choices["to"] else None}
    if stage == "nominate":
        return {"target": None}
    return {"vote": stage == "move_vote" or seat == removal_yes}


def trial(model, focal, team, challenge, out, hand=None):
    peer, session = position(focal, team, challenge, hand)
    t = peer.table
    first = t.revision
    answer = private_check(session, model, hand is not None)
    full = challenge and team == "red" and focal == 3
    receipts = []
    while not t.game.winner:
        rev = t.revision
        if t.speaking(focal, peer.now):
            receipts.append(
                {"revision": rev, "phase": "discussion", "calls": act(session, model, True)}
            )
        if t.revision != rev:
            continue
        peer.now = max(peer.now, t.opens)
        for seat in t.game.alive.copy():
            choices = t.choices(seat, peer.now)
            if seat != focal and choices:
                t.submit(
                    seat,
                    rev,
                    peers_choice(t.game.stage, seat, choices, 1 if hand is None else 2),
                    peer.now,
                )
                if t.revision != rev:
                    break
        if t.revision == rev and t.choices(focal, peer.now):
            receipts.append(
                {"revision": rev, "phase": "decision", "calls": act(session, model, False)}
            )
        if t.revision == rev:
            peer.now = t.deadline
            t.tick(peer.now)
        if not full:
            break
    outcome = t.record["events"][first]
    assert outcome["kind"] == "eliminate_vote"
    remarks = [
        r["text"]
        for r in t.record.get("remarks", [])
        if r["seat"] == focal and r["after_event"] == first
    ]
    if full:
        assert replay(t.record).winner
        (out / "game.json").write_text(json.dumps(t.record, indent=2) + "\n")
    elif not challenge and team == "red" and focal == 3:
        (out / "open-defense.json").write_text(json.dumps(t.record, indent=2) + "\n")
    return {
        "seat": focal,
        "team": team,
        "challenge": challenge,
        **({"held_face": hand} if hand is not None else {}),
        "private_answer": answer,
        "remark": next(iter(remarks), None),
        "own_removal_vote": outcome["votes"][focal],
        "receipts": receipts,
    }


def run(model, out, hands):
    out.mkdir()
    request(
        11434,
        "/api/chat",
        {
            "model": model,
            "messages": [],
            "stream": False,
            "keep_alive": "10m",
            "options": {"num_ctx": CONTEXT},
        },
        120,
    )
    (out / "model.json").write_text(
        json.dumps({"model": model, "resident": resident_model(model)}, indent=2) + "\n"
    )
    with (out / "cases.jsonl").open("x") as log:
        if hands:
            for hand in (255, 0):
                for team in ("blue", "red"):
                    print(json.dumps(trial(model, 1, team, True, out, hand)), file=log, flush=True)
            return
        for challenge in (False, True):
            for focal in (2, 3):
                for team in ("blue", "red"):
                    print(
                        json.dumps(trial(model, focal, team, challenge, out)), file=log, flush=True
                    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model")
    parser.add_argument("out", type=Path)
    parser.add_argument("--hands", action="store_true")
    args = parser.parse_args()
    run(args.model, args.out, args.hands)
