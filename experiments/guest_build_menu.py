"""Compare literal placements and their geometric effects on an identical reduced menu."""

import argparse
import csv
import json
from itertools import product
from pathlib import Path

from experiments.action_probe import GUEST, ROOT, answer, position
from experiments.skill_probe import MODEL
from footsteps.board import moves, optimistic_length, rotate
from footsteps.ollama import INDEX_INSTRUCTIONS, model_request
from footsteps.solo import sealed
from footsteps.team_names import color_brief


def representatives(snap):
    state, options = snap["state"], snap["choices"]
    board = dict(state["board"])
    marker, goal = state["marker"], state["goal"]
    assert state["store_count"] > 0  # These positions all drew two and will return one.
    menu = {}
    for tile, turns, at in product(
        dict.fromkeys(state["hand"]), options["rotation"], options["at"]
    ):
        after = {**board, at: rotate(tile, turns)}
        if sealed(after, marker, goal):
            result = "marker permanently trapped"
        elif any(
            optimistic_length(after, dest, goal, state["store_count"] + 1) is not None
            for dest in moves(after, marker)
        ):
            result = "step available with a possible route to EXIT"
        else:
            result = "no immediate step with a route within the remaining turns"
        menu.setdefault(result, {"tile": tile, "rotation": turns, "at": at})
    return menu


def positions(transfer):
    if transfer:
        for seed, red in product((8101, 8102), (1, 2)):
            source = ROOT / f"social/fresh-base/{seed}-bad{red}.json"
            yield source.stem, False, position(source, 10, 2)
    else:
        for blue, rotated in product((False, True), repeat=2):
            yield GUEST.stem, rotated, position(GUEST, 23, 2, blue=blue, rotated_hand=rotated)


def run(path, arms, transfer):
    with path.open("x") as out:
        rows = csv.writer(out, lineterminator="\n")
        rows.writerow(["source", "role", "rotated_hand", "arm", "reversed", "choice", "effect"])
        for source, rotated, snap in positions(transfer):
            menu = representatives(snap)
            assert len(menu) == 3
            for arm, reverse in product(arms, (False, True)):
                items = list(menu.items())[:: -1 if reverse else 1]
                body = model_request(snap, MODEL, explicit_actions=True)
                body["think"] = False
                system, user = body["messages"]
                system["content"] = system["content"].replace(
                    INDEX_INSTRUCTIONS, "Choose one complete legal placement by its name."
                )
                ctx = json.loads(user["content"])
                names = [f"build_{i}" for i in range(len(items))]
                if arm in ("named", "payoff"):
                    names = [effect.replace(" ", "_") for effect, _ in items]
                if arm == "payoff":
                    names = [
                        "seal_marker__Red_win_assured" if e == "marker permanently trapped" else n
                        for n, (e, _) in zip(names, items, strict=True)
                    ]
                    system["content"] += (
                        " If the marker is permanently trapped, Blue can never reach EXIT. "
                        "Red wins even if all Red players are later removed."
                    )
                ctx["options"] = [
                    {"name": name, **choice, **({"effect": effect} if arm != "literal" else {})}
                    for name, (effect, choice) in zip(names, items, strict=True)
                ]
                user["content"] = json.dumps(ctx, separators=(",", ":"))
                body["format"] = {
                    "type": "object",
                    "properties": {"build": {"type": "string", "enum": names}},
                    "required": ["build"],
                    "additionalProperties": False,
                }
                color_brief(body)
                effect, choice = items[names.index(answer(body)["build"])]
                rows.writerow(
                    [
                        source,
                        snap["state"]["role"],
                        rotated,
                        arm,
                        reverse,
                        json.dumps(choice),
                        effect,
                    ]
                )
                out.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--arms",
        nargs="+",
        choices=("literal", "effects", "named", "payoff"),
        default=("literal", "effects", "named", "payoff"),
    )
    parser.add_argument(
        "--transfer",
        action="store_true",
        help="use two archived three-seat deals with both alignments",
    )
    args = parser.parse_args()
    run(args.output, args.arms, args.transfer)
