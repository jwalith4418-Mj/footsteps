"""Matched literal commits and private orientation on local readings and social tactics."""

import argparse
import json
from itertools import product
from pathlib import Path
from time import monotonic

from experiments.action_probe import ROOT, position
from experiments.rotation_probe import cases, pick, success
from experiments.skill_probe import MODEL
from footsteps.action_tools import action_request, apply_call, build_tools, native_decision
from footsteps.ollama import request


def panel():
    yield from cases()
    yield "Blue-82-escape", position(ROOT / "rotation/social/8602-red1+3.json", 21, 2), "", None


def one_call(snap, model, task, structured, log):
    specs = [build_tools(snap, "direct")[0]]
    body = action_request(snap, model, specs, task=task)
    if structured:
        fn = body.pop("tools")[0]["function"]
        body["format"] = fn["parameters"]
        system = body["messages"][0]
        system["content"] = system["content"].split(" Act by calling")[0] + (
            " Commit a placement by returning the place_tile arguments as a JSON object. "
            "Give a literal piece handle, clockwise rotation (0 to 3), and x and y coordinates."
        )
    result = request(11434, "/api/chat", body, 30)
    if structured:
        args = json.loads(result["message"]["content"])
    else:
        calls = result["message"].get("tool_calls", [])
        if len(calls) != 1 or calls[0]["function"]["name"] != "place_tile":
            raise ValueError("no single place_tile call")
        args = calls[0]["function"]["arguments"]
    if not (
        isinstance(args, dict)
        and set(args) == {"piece", "rotation", "x", "y"}
        and isinstance(args["piece"], str)
        and all(type(args[k]) is int for k in ("rotation", "x", "y"))
    ):
        raise ValueError("malformed literal placement")
    _, choice, _ = apply_call(
        "place_tile", args, snap["state"], snap["choices"], snap["pieces"], "direct", None
    )
    log.append({"name": "place_tile", "status": "commit", "arguments": args})
    return choice


def run(path, model, arms, tactics_only, *, panels=None, paired_order=False):
    with path.open("x") as f:
        for i, (name, snap, task, target) in enumerate(panel() if panels is None else panels):
            if tactics_only and target is not None:
                continue
            for reverse in (bool((i // 2) % 2),) if paired_order else (False, True):
                for offset in range(len(arms)):
                    arm = arms[(i + int(reverse) + offset) % len(arms)]
                    started = monotonic()
                    log = []
                    choice = {}
                    status = "accepted"
                    opts = snap["choices"]
                    view = {
                        **snap,
                        "choices": {k: v[::-1] if reverse else v for k, v in opts.items()},
                        "pieces": dict(
                            list(snap["pieces"].items())[::-1]
                            if reverse
                            else snap["pieces"].items()
                        ),
                    }
                    try:
                        if arm == "menu":
                            choice, info = pick(snap, model, "ordinary", task, reverse, False)
                            status = info["status"]
                        else:
                            if arm in ("literal", "single"):
                                result = one_call(view, model, task, arm == "literal", log)
                            else:
                                mode = {"informed": "draft", "cued": "hand"}.get(arm, arm)
                                result = native_decision(
                                    view,
                                    model,
                                    30,
                                    mode=mode,
                                    cue=arm == "cued",
                                    trace=log,
                                    task=task,
                                    prospects=arm == "informed",
                                )
                            h = result["piece"]
                            choice = {
                                "tile": view["pieces"][h][0],
                                "rotation": result.get(
                                    "rotation", result.get("expected_orientation")
                                ),
                                "at": result["at"],
                            }
                        if monotonic() - started >= 30 and status == "accepted":
                            raise TimeoutError("late model action")
                    except (OSError, ValueError) as exc:
                        choice = {}
                        status = str(exc)
                    score = bool(choice) and success(
                        snap["state"],
                        choice["tile"],
                        choice["rotation"],
                        tuple(choice["at"]),
                        target,
                    )
                    viable = sum(
                        success(snap["state"], face, turn, at, target)
                        for face, turn, at in product(opts["tile"], opts["rotation"], opts["at"])
                    )
                    row = {
                        "case": name,
                        "reverse": reverse,
                        "model": model,
                        "arm": arm,
                        "status": status,
                        "choice": choice,
                        "success": score,
                        "viable": viable,
                        "calls": log,
                        "seconds": round(monotonic() - started, 3),
                    }
                    f.write(json.dumps(row, separators=(",", ":")) + "\n")
                    f.flush()


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--model", default=MODEL)
    p.add_argument(
        "--arms",
        nargs="+",
        choices=("menu", "direct", "hand", "literal", "single", "draft", "informed", "fit", "cued"),
        default=("menu", "direct", "hand"),
    )
    p.add_argument("--tactics-only", action="store_true")
    args = p.parse_args()
    run(args.output, args.model, args.arms, args.tactics_only)
