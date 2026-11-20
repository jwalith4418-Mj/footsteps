"""Test actual legal placement on the guest's third turn, with opposite objectives."""

import argparse
import csv
import json
from pathlib import Path

from experiments.action_probe import GUEST, position
from experiments.skill_probe import MODEL
from footsteps.board import moves, optimistic_length, rotate
from footsteps.ollama import consultation, model_request, request
from footsteps.seat_tools import blocking_tile
from footsteps.solo import sealed


def run(path):
    with path.open("x") as out:
        rows = csv.writer(out, lineterminator="\n")
        rows.writerow(
            [
                "role",
                "rotated_hand",
                "arm",
                "reversed",
                "at",
                "tile",
                "rotation",
                "sealed",
                "route_open",
                "tools",
            ]
        )
        for blue in (False, True):
            for rotated in (False, True):
                snap = position(GUEST, 23, 2, blue=blue, rotated_hand=rotated)
                state = snap["state"]
                marker, goal = tuple(state["marker"]), tuple(state["goal"])
                board = dict(state["board"])
                for arm in ("legacy", "brief", "voluntary", "shown"):
                    for rev in (False, True):
                        options = {k: v[::-1] if rev else v for k, v in snap["choices"].items()}
                        view = {**snap, "choices": options}
                        body = model_request(
                            view, MODEL, guided=True, explicit_actions=arm != "legacy", explain=True
                        )
                        body["think"] = False
                        used = []
                        if arm == "shown":
                            report = blocking_tile(board, marker, goal, state["hand"])
                            ctx = json.loads(body["messages"][1]["content"])
                            ctx["placement_that_permanently_seals_marker"] = {
                                k: options[k].index(v) for k, v in report.items()
                            }
                            body["messages"][1]["content"] = json.dumps(ctx, separators=(",", ":"))
                        if arm == "voluntary":
                            messages, used = consultation(view, body, 15)
                            body["messages"].extend(messages)
                        reply = json.loads(
                            request(11434, "/api/chat", body, 30)["message"]["content"]
                        )
                        if any(
                            type(reply[k]) is not int or not 0 <= reply[k] < len(v)
                            for k, v in options.items()
                        ):
                            raise ValueError("invalid placement index")
                        choice = {k: v[reply[k]] for k, v in options.items()}
                        after = {
                            **board,
                            tuple(choice["at"]): rotate(choice["tile"], choice["rotation"]),
                        }
                        # One tile returns after this draw, then each later turn allows one step.
                        left = state["store_count"] + 1
                        route = any(
                            optimistic_length(after, to, goal, left) is not None
                            for to in moves(after, marker)
                        )
                        rows.writerow(
                            [
                                state["role"],
                                rotated,
                                arm,
                                rev,
                                choice["at"],
                                choice["tile"],
                                choice["rotation"],
                                sealed(after, marker, goal),
                                route,
                                json.dumps(used),
                            ]
                        )
                        out.flush()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    run(parser.parse_args().output)
