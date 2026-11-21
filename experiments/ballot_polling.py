"""Compare ballot history replies and waiting tool names on frozen seat projections."""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.game_efficiency import MODEL
from experiments.rana_speakers import SpeakerSeat
from footsteps.record import read
from footsteps.session import Session
from footsteps.table import Table

WAIT_NAMES = {
    "guided": "wait",
    "plain": "wait",
    "named": "wait_for_change",
    "await": "await_change",
    "poll": "poll",
    "monitor": "monitor",
}
SOURCE = Path(__file__).parent / "required-wait/early/game.json"


class ProbeSession(Session):
    def __init__(self, peer, variant):
        self.variant = variant
        super().__init__(
            peer, sleep=peer.expire, inspect_rotations=True, movement_context=True, context=32768
        )

    def tools(self):
        tools = super().tools()
        if WAIT_NAMES[self.variant] != "wait":
            for tool in tools:
                if tool["function"]["name"] == "wait":
                    tool["function"]["name"] = WAIT_NAMES[self.variant]
        return tools

    def ballot_guidance(self):
        text = super().ballot_guidance()
        return text.replace("wait()", f"{WAIT_NAMES[self.variant]}()")

    def execute(self, name, args, offered, revision):
        if (
            name != "wait"
            and name == WAIT_NAMES[self.variant]
            and any(t["function"]["name"] == name for t in offered)
        ):
            # Translate only the offered native function, after the model has chosen it.
            name = "wait"
            offered = [t for t in super().tools() if t["function"]["name"] == "wait"]
        result = super().execute(name, args, offered, revision)
        if self.variant == "plain":
            result.pop("pending_ballot", None)
        return result


def position(revision, phase):
    record = read(SOURCE)
    table = Table(
        record["setup"], Random("draw/11301"), seconds=45, discussion=30, early_ballot=True
    )
    peer = SpeakerSeat(table, 2)
    for i in (0, 1):
        table.join(i, 0)
    assert table.record["events"] == record["events"][:1]
    for event in record["events"][1:revision]:
        table.commit(event)
        if table.game.stage == "move_vote":
            table.open_decision(0)
            for remark in record["remarks"]:
                if remark["after_event"] == table.revision:
                    table.say(remark["seat"], table.revision, remark["text"], 0)
    if phase == "off_turn":
        table.open_decision(0)
        assert table.game.stage == "place" and table.game.actor != peer.seat
    if phase != "discussion":
        peer.now = table.opens
    if phase == "submitted":
        table.submit(2, revision, {"vote": True}, peer.now)
    return peer


def trial(revision, phase, variant):
    peer = position(revision, phase)
    s = ProbeSession(peer, variant)
    scripted = {"name": "history", "arguments": {"kind": "move_vote", "limit": 6}}
    if phase == "off_turn":
        scripted = {"name": "get_state", "arguments": {}}
    page = s.step(MODEL, infer=lambda *_: {"message": {"tool_calls": [{"function": scripted}]}})[
        "result"
    ]
    ids = [e["id"] for e in page["entries"]] if "entries" in page else None
    if phase != "off_turn":
        assert ids == ([] if revision == 4 else [7])
    calls = []
    for _ in range(5):
        row = s.step(MODEL, budget=45)
        tool = row["tool"] if row["tool_offered"] else "unavailable"
        calls.append(
            {
                "tool": tool,
                "error": "error" in row["result"],
                "force": tool in WAIT_NAMES.values() and row["arguments"].get("force") is True,
            }
        )
        if "error" not in row["result"] and (
            tool in ("speak", "vote_move")
            or (phase == "discussion" and s.snap["phase"] != "discussion")
            or s.snap["revision"] != revision
        ):
            break
    return {
        "revision": revision,
        "phase": phase,
        "variant": variant,
        "entries": ids,
        "calls": calls,
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument(
        "--off-turn", action="store_true", help="compare waiting names after a fresh board read"
    )
    args = cli.parse_args()
    with args.output.open("x") as out:
        revisions = (1, 9) if args.off_turn else (4, 12)
        phases = ("off_turn",) if args.off_turn else ("discussion", "due", "submitted")
        variants = (
            ("guided", "named", "await", "poll", "monitor")
            if args.off_turn
            else ("guided", "plain", "named", "await")
        )
        for rev in revisions:
            for phase in phases:
                for variant in variants:
                    print(json.dumps(trial(rev, phase, variant)), file=out, flush=True)
