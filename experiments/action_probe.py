"""Probe a known guest tactic and disputed public actions from replay-derived private views."""

import argparse
import csv
import json
from pathlib import Path
from random import Random

from experiments.skill_probe import MODEL
from footsteps.action_language import action_brief
from footsteps.board import rotate
from footsteps.ollama import INDEX_INSTRUCTIONS, consultation, model_request, request
from footsteps.record import read
from footsteps.seat_tools import query
from footsteps.table import Table
from footsteps.team_names import color_brief

ROOT = Path(__file__).parent
GUEST = ROOT / "blind-guest/game/1244867160-bad1+2.json"
SOCIAL = ROOT / "public-discussion/five-colors/8602-bad1+3.json"


def position(source, count, seat, *, two_exits=False, later=False, rotated_hand=False, blue=False):
    record = read(source)
    setup = record["setup"]
    events = record["events"][:count]
    if two_exits:
        setup["hands"][1][0] = 101  # Same entrances as 37, with another exit back to START.
        events[11] = {**events[11], "tile": 101}
    if rotated_hand:
        setup["hands"][2][0] = rotate(246, 1)
    if blue:
        setup["roles"][2], setup["roles"][3] = setup["roles"][3], setup["roles"][2]
    if later:
        for key in ("roles", "hands"):
            setup[key][2], setup[key][3] = setup[key][3], setup[key][2]
    table = Table(setup, Random(0), color_teams=True)
    table.started = True
    for event in events:
        table.commit(event)
    # Reinsert public statements at their recorded position in the seat history.
    for remark in reversed(record.get("remarks", [])):
        rev = remark["after_event"]
        if rev <= count:
            log = table.history[seat]
            i = next(i for i, row in enumerate(log) if row["event"] == rev)
            log.insert(
                i + 1,
                {
                    "event": rev,
                    "turn": log[i]["turn"],
                    "text": f"P{remark['seat']}: {remark['text']}",
                },
            )
    table.opens = 0
    table.deadline = 60
    return table.view(seat, 0)


def cases():
    for extra in (False, True):
        for later in (False, True):
            snap = position(GUEST, 14, 3 if later else 2, two_exits=extra, later=later)
            yield (
                f"trap-{int(extra)}-later-{int(later)}",
                snap,
                "Assume the proposed step succeeds and all seats survive. Can YOU, on the very next build, use a tile already in YOUR hand to block every immediate exit from that landing?",
                ["yes", "no"],
                "yes" if not extra and not later else "no",
                "compare_landings",
                {},
            )
    for name, rev, seat, question, opts, expected in (
        (
            "after-placement",
            24,
            2,
            "Where is the marker immediately after the placement?",
            ["(1,1)", "(0,1)"],
            "(0,1)",
        ),
        (
            "pending-step",
            14,
            2,
            "Where is the marker before this ballot resolves?",
            ["(0,0)", "(0,1)"],
            "(0,0)",
        ),
        (
            "resolved-step",
            15,
            2,
            "Where is the marker after the revealed movement ballot?",
            ["(0,0)", "(0,1)"],
            "(0,1)",
        ),
    ):
        yield name, position(GUEST, rev, seat), question, opts, expected, None, {}
    for name, builder, expected in (("false-accusation", 2, "0"), ("actual-builder", 1, "1")):
        yield (
            name,
            position(SOCIAL, 23, 4),
            f"How many times did P{builder} choose stay as builder before this removal ballot?",
            ["0", "1", "2", "3"],
            expected,
            "check_builder_turns",
            {"builder": builder},
        )


def answer(body):
    return json.loads(request(11434, "/api/chat", body, 30)["message"]["content"])


def run(path):
    with path.open("x") as out:
        w = csv.writer(out, lineterminator="\n")
        w.writerow(["case", "arm", "reversed", "expected", "answer", "tools"])
        for case, snap, question, options, expected, tool, args in cases():
            for arm in ("legacy", "brief", "voluntary", "shown") if tool else ("legacy", "brief"):
                for reverse in (False, True):
                    body = model_request(snap, MODEL)
                    body["think"] = False
                    color_brief(body)
                    system, user = body["messages"]
                    system["content"] = system["content"].replace(
                        INDEX_INSTRUCTIONS,
                        "Answer the factual question using this seat's information.",
                    )
                    if arm != "legacy":
                        system["content"] += " " + action_brief(snap["state"])
                    ctx = json.loads(user["content"])
                    opts = options[::-1] if reverse else options
                    ctx.update(question=question, answers=opts)
                    if arm == "shown":
                        ctx["referee_lookup"] = query(snap, tool, args)
                    user["content"] = json.dumps(ctx, separators=(",", ":"))
                    body["format"] = {
                        "type": "object",
                        "properties": {"answer": {"type": "string", "enum": opts}},
                        "required": ["answer"],
                        "additionalProperties": False,
                    }
                    used = []
                    if arm == "voluntary":
                        messages, used = consultation(snap, body, 15)
                        body["messages"].extend(messages)
                    w.writerow(
                        [case, arm, reverse, expected, answer(body)["answer"], json.dumps(used)]
                    )
                    out.flush()
        for stage, snap, intentions in (
            (
                "movement",
                position(GUEST, 14, 2),
                [
                    "You want the marker to stay here.",
                    "You want the marker to take the requested step.",
                ],
            ),
            (
                "removal",
                position(SOCIAL, 23, 4),
                [
                    "You want the named nominee to continue playing.",
                    "You want the named nominee eliminated.",
                ],
            ),
        ):
            for brief in (False, True):
                for value in (False, True):
                    for reverse in (False, True):
                        votes = [False, True] if reverse else [True, False]
                        view = {**snap, "choices": {"vote": votes}}
                        body = model_request(
                            view, MODEL, named_ballots=True, explicit_actions=brief
                        )
                        body["think"] = False
                        color_brief(body)
                        body["messages"][0]["content"] += (
                            " For this ballot interpretation test, follow this intention. "
                            + intentions[value]
                        )
                        labels = body["format"]["properties"]["vote"]["enum"]
                        chosen = answer(body)["vote"]
                        w.writerow(
                            [
                                stage + "-intent-" + str(value),
                                "brief" if brief else "legacy",
                                reverse,
                                value,
                                votes[labels.index(chosen)],
                                "[]",
                            ]
                        )
                        out.flush()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    run(cli.parse_args().output)
