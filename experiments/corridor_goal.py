"""Separate predicting a step, planning toward EXIT and executing a self-authored plan."""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.skill_probe import MODEL
from footsteps.action_tools import action_request, native_decision
from footsteps.game import with_exit_origin
from footsteps.ollama import request
from footsteps.table import Table


def answer(snap, model, question, fields):
    body = action_request(snap, model, [])
    del body["tools"]
    body["messages"][0]["content"] = body["messages"][0]["content"].split(" Act by calling")[0]
    body["messages"].append({"role": "user", "content": question})
    body["format"] = {
        "type": "object",
        "properties": {key: {"type": kind} for key, kind in fields.items()},
        "required": list(fields),
        "additionalProperties": False,
    }
    return json.loads(request(11434, "/api/chat", body, 30)["message"]["content"])


def run(output, model, verified=False):
    with output.open("x") as out:
        for heading, goal, away in (("north", [0, 2], [0, -3]), ("east", [2, 0], [-3, 0])):
            t = Table(
                with_exit_origin(
                    {"roles": ["blue"], "goal": goal, "hands": [[65]], "store": [65, 65]}
                ),
                Random(9501),
            )
            t.join(0, 0)
            snap = t.view(0, 0)
            expected = [v // -2 for v in goal]
            rotation = 2 if heading == "north" else 3
            winning = {
                "exit_x": 0,
                "exit_y": 0,
                "first_x": expected[0],
                "first_y": expected[1],
                "rotation": rotation,
            }
            prediction = None
            if verified:
                plan = winning
                source = "A verified winning plan for this position is"
            else:
                source = "Your own proposed plan from this position was"
                prediction = answer(
                    snap,
                    model,
                    f"Suppose the marker takes its first step to {away}. Report its Manhattan distance to EXIT before and after that step. There are two movement opportunities including this one. Could this line still win?",
                    {
                        "distance_before": "integer",
                        "distance_after": "integer",
                        "can_still_win": "boolean",
                    },
                )
                plan = answer(
                    snap,
                    model,
                    "You have two movement opportunities including this one. Work backward from winning. Give the EXIT coordinates, where the marker must land on the first step, and the absolute clockwise quarter turns for the straight tile to build there so you can complete the walk.",
                    dict.fromkeys(
                        ("exit_x", "exit_y", "first_x", "first_y", "rotation"), "integer"
                    ),
                )
            trace = []
            result = {}
            try:
                result = native_decision(
                    snap,
                    model,
                    30,
                    mode="hand",
                    trace=trace,
                    task=f"{source} {json.dumps(plan)}. You can revise it. Choose your actual placement.",
                )
            except (OSError, ValueError) as exc:
                result["error"] = str(exc)
            row = {
                "heading": heading,
                "model": model,
                "prediction": prediction,
                "plan": plan,
                "choice": result,
                "calls": trace,
                "prediction_correct": prediction
                == {"distance_before": 2, "distance_after": 3, "can_still_win": False},
                "plan_correct": plan == winning,
                "placement_correct": result.get("at") == expected
                and result.get("expected_orientation") == rotation,
            }
            if verified:
                del row["prediction"], row["prediction_correct"], row["plan_correct"]
            out.write(json.dumps(row, separators=(",", ":")) + "\n")
            out.flush()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument(
        "--verified", action="store_true", help="supply the verified first square and absolute turn"
    )
    args = cli.parse_args()
    run(args.output, args.model, args.verified)
