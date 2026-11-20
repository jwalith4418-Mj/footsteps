"""Test reputation and role-sensitive choices on frozen, referee-legal seat views."""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.behavior_context import STRATEGIES, apply_strategy
from experiments.skill_probe import MODEL
from experiments.social_evidence import write_rows
from experiments.social_prompt import social_choice
from footsteps.decision_notes import open_private, save_note
from footsteps.ollama import infer, model_request, request
from footsteps.record import read
from footsteps.solo import sealed
from footsteps.table import Table

SOURCE = Path(__file__).with_name("social") / "debate-role/8201-red1.json"


def prefix(setup, events):
    table = Table(setup, Random(0), discussion=1)
    table.started = True
    for event in events:
        table.commit(event)
    table.open_decision(0)
    return table


def cases():
    record = read(SOURCE)
    exact = prefix(record["setup"], record["events"][:15])
    for line in record["remarks"]:
        if line["after_event"] == exact.revision:
            exact.say(line["seat"], exact.revision, line["text"], 0)
    yield "8201-self", exact.view(1, exact.opens), False
    for red in (1, 2):
        setup = {**record["setup"], "roles": ["red" if s == red else "blue" for s in range(3)]}
        opening = prefix(setup, record["events"][:4])
        yield "ordinary-move", opening.view(red, opening.opens), None
        yield "ordinary-move", opening.view(3 - red, opening.opens), True
        quiet = prefix(setup, [*record["events"][:4], {"kind": "move_vote", "votes": [True] * 3}])
        yield "quiet-opening", quiet.view(1, quiet.opens), None

    # Same three-seat rules, short floors for consequences that can be checked exactly.
    for blue in (0, 2):
        roles = ["blue" if i == blue else "red" for i in range(3)]
        setup = {"goal": [0, 1], "roles": roles, "hands": [[8], [8], [8]], "store": [32, 32]}
        events = [
            {"kind": "draw", "tiles": [32, 32]},
            {"kind": "place", "tile": 8, "at": [1, 0], "rotation": 0},
            {"kind": "discard", "tile": 32},
        ]
        red = 2 - blue
        for case, dest in (("enter-exit", [0, 1]), ("seal-marker", [1, 0])):
            table = prefix(setup, [*events, {"kind": "propose", "to": dest}])
            for seat in (blue, red):
                yield case, table.view(seat, table.opens), (seat == blue) == (case == "enter-exit")
        for label, dest, target in (("last-blue", None, blue), ("sealed-self", [1, 0], red)):
            history = [*events, {"kind": "propose", "to": dest}]
            if dest:
                history.append({"kind": "move_vote", "votes": [True, True, True]})
            table = prefix(setup, history)
            if dest:
                assert sealed(table.game.board, table.game.marker, table.game.goal)
            # P1 nominates in one seating; advance the other to P0 or P2.
            nominator = 1 if blue == 0 else 2 if target != 2 else 0
            while table.game.queue[0] != nominator:
                table.commit({"kind": "nominate", "target": None})
            table.submit(nominator, table.revision, {"target": target}, table.opens)
            for seat in (red, blue) if not dest else (red,):
                yield label, table.view(seat, table.opens), None if dest else seat == red


def tradeoffs():
    record = read(SOURCE)
    for focal in (1, 2):
        roles = ["red" if s == focal else "blue" for s in range(3)]
        opening = prefix({**record["setup"], "roles": roles}, record["events"][:4])
        for s in (0, 3 - focal):
            opening.say(
                s,
                opening.revision,
                "I intend to vote yes. I will nominate anyone who votes no on this opening step.",
                0,
            )
        yield "free-cover", opening.view(focal, opening.opens), True

        setup = {"goal": [0, 1], "roles": roles, "hands": [[8], [8], [8]], "store": [32, 32]}
        table = prefix(
            setup,
            [
                {"kind": "draw", "tiles": [32, 32]},
                {"kind": "place", "at": [1, 0], "tile": 8, "rotation": 0},
                {"kind": "discard", "tile": 32},
                {"kind": "propose", "to": [1, 0]},
            ],
        )
        table.say(0, table.revision, "I intend to vote yes.", 0)
        table.say(
            3 - focal,
            table.revision,
            "I intend to vote no. East seals the marker. If it passes, I will nominate anyone supporting it.",
            0,
        )
        yield "win-at-risk", table.view(focal, table.opens), True


def decide(snap, model, strategy, sink, reverse=False):
    if strategy == "assisted":
        if reverse:
            key, values = next(iter(snap["choices"].items()))
            snap = {**snap, "choices": {key: list(reversed(values))}}
        return infer(snap, model, 30, no_think=True, outcome_policy=True, note_file=sink)
    if snap["state"]["stage"] != "move_vote":
        return social_choice(
            snap, model, "receipt", sink, reverse=reverse, red_brief=True, strategy=strategy
        )
    options = snap["choices"]["vote"]
    if reverse:
        options = list(reversed(options))
    snap = {**snap, "choices": {"vote": options}}
    body = model_request(snap, model, guided=True, named_ballots=True, explain=True)
    body["think"] = False
    apply_strategy(body, snap, strategy)
    reply = json.loads(request(11434, "/api/chat", body, 30)["message"]["content"])
    vote = {"vote": options[body["format"]["properties"]["vote"]["enum"].index(reply["vote"])]}
    save_note(sink, snap, model, vote, reply["reason"], [])
    return vote


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--strategy", required=True, choices=STRATEGIES)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument(
        "--tradeoffs",
        action="store_true",
        help="two publicly announced voting dilemmas in exchanged seats",
    )
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--private-notes", type=Path, required=True)
    args = cli.parse_args()
    request(
        11434,
        "/api/generate",
        {"model": args.model, "stream": False, "options": {"num_ctx": 4096}},
        180,
    )
    rows = []
    with open_private(args.private_notes) as sink:
        for case, snap, preferred in tradeoffs() if args.tradeoffs else cases():
            for reverse in (False, True):
                action = decide(snap, args.model, args.strategy, sink, reverse)
                rows.append(
                    {
                        "case": case,
                        "seat": snap["seat"],
                        "role": snap["state"]["role"],
                        "reverse": reverse,
                        "preferred": preferred,
                        "choice": next(iter(action.values())),
                    }
                )
    write_rows(args.out, rows)


if __name__ == "__main__":
    main()
