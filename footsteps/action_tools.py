"""Native Ollama calls on one authenticated decision and the builder's private hand."""

import json
import time
from http.client import HTTPException

from .board import moves, optimistic_length, rotate
from .decision_notes import save_note
from .game import checked_placement, require
from .ollama import RULES, forward_examples, model_request, request
from .seat_tools import tile
from .solo import sealed
from .team_names import color_brief

PREPARATIONS = {"orient_tile", "preview_placement", "inspect_rotations_at"}


def function(name, description, fields):
    properties = {k: {"type": v} for k, v in fields.items()}
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": list(fields),
                "additionalProperties": False,
            },
        },
    }


def build_tools(snapshot, mode):
    stage = snapshot["state"]["stage"]
    square = {"x": "integer", "y": "integer"}
    piece = {"piece": "string"}
    turns = {"rotation": "integer"}
    if stage == "place":
        args = piece | (turns if mode == "direct" else {}) | square
        check = {}
        if "can_step" in snapshot["choices"]:
            check = {"origin_x": "integer", "origin_y": "integer", "can_step": "boolean"}
        if "marker_on_origin" in snapshot["choices"]:
            check["marker_on_origin"] = "boolean"
        tools = [
            function(
                "place_tile",
                "Commit this held piece at the literal empty square. The marker stays put. A rotation is an absolute count of clockwise quarter turns, 0 through 3.",
                args | check,
            ),
            function(
                "preview_placement",
                "Privately see the result of placing this piece at the square, including actual marker access. Leaves the floor unchanged.",
                args,
            ),
        ]
        if mode == "draft":
            tools[0] = function(
                "commit_preview",
                "Commit exactly the last previewed piece, square and orientation. Preview again after changing that piece.",
                check,
            )
        if mode == "fit":
            tools.append(
                function(
                    "inspect_rotations_at",
                    "For this one held piece and empty square, compare the four clockwise orientations and whether the marker could step onto it. Leaves the piece in hand as it was.",
                    piece | square,
                )
            )
        if mode in ("hand", "draft", "fit"):
            tools.append(
                function(
                    "orient_tile",
                    "Set one held piece to an absolute clockwise quarter turn count (0 to 3). Read its new entry and exit sides. Keeps the piece in hand.",
                    piece | turns,
                )
            )
        return tools
    if stage == "discard":
        return [function("return_tile", "Privately return one held piece to the store.", piece)]
    if stage == "propose":
        return [
            function(
                "propose_step", "Propose that the marker step to these literal coordinates.", square
            ),
            function("stay", "Keep the marker here.", {}),
        ]
    if stage == "nominate":
        return [
            function(
                "nominate", "Nominate a different living seat for removal.", {"seat": "integer"}
            ),
            function("pass_nomination", "Decline your nomination opportunity.", {}),
        ]
    movement = stage == "move_vote"
    return [
        function(
            "vote_move" if movement else "vote_removal",
            "Cast a public ballot. True approves the pending step."
            if movement
            else "Cast a public ballot. True removes the nominee.",
            {"approve": "boolean"},
        )
    ]


def receipt(handle, face, rotation):
    _, entrances, exits = tile(rotate(face, rotation))
    return {
        "piece": handle,
        "face": face,
        "rotation": rotation,
        "entrances": entrances,
        "exits": exits,
    }


def route_prospects(state, preview):
    """Optimistic reachability after this build and the still-pending proposal."""
    board = {tuple(p): face for p, face in state["board"]}
    board[tuple(preview["at"])] = rotate(preview["face"], preview["rotation"])
    marker, goal = tuple(state["marker"]), tuple(state["goal"])
    remaining = state["store_count"] + int(state["draw_count"] == 2)
    limit = min(16, remaining)
    label = (
        "possible_route_in_time" if remaining <= 16 else "possible_route_within_16_further_steps"
    )
    return {
        "permanent_trap": sealed(board, marker, goal),
        label: any(
            optimistic_length(board, p, goal, limit) is not None
            for p in (marker, *moves(board, marker))
        ),
    }


def apply_call(name, args, state, choices, pieces, mode, orient):
    """Apply private preparations and translate a commit into the referee's vocabulary."""
    result = canonical = None
    handle = args.get("piece")
    choice = None
    if handle is not None:
        require(handle in pieces, "unknown held piece")
        face, current = pieces[handle]
        rotation = args.get("rotation", current)
        require(rotation in range(4), "rotation must be 0 to 3")
        if name == "orient_tile":
            if orient:
                orient(handle, rotation)
            pieces[handle] = (face, rotation)
            result = receipt(handle, face, rotation)
        elif name == "return_tile":
            choice = {"piece": handle}
            canonical = {"tile": face}
        else:
            at = (args["x"], args["y"])
            require(
                at in map(tuple, choices["at"]),
                "choose an empty build square listed in your view",
            )
            board = {tuple(p): f for p, f in state["board"]}
            marker = tuple(state["marker"])
            if name == "inspect_rotations_at":
                rows = []
                for turns in range(4):
                    board[at] = rotate(face, turns)
                    rows.append(
                        {
                            **receipt(handle, face, turns),
                            "can_step_here": at in moves(board, marker),
                        }
                    )
                result = {
                    "at": at,
                    "marker_stays": marker,
                    "orientations": rows,
                    "held_rotation": current,
                }
            elif name == "preview_placement":
                board[at] = rotate(face, rotation)
                steps = moves(board, marker)
                result = {
                    **receipt(handle, face, rotation),
                    "at": at,
                    "marker_stays": marker,
                    "can_step_here": at in steps,
                    "legal_steps_after_build": steps,
                }
            else:
                canonical = {"tile": face, "rotation": rotation, "at": list(at)}
                choice = {
                    "piece": handle,
                    "at": list(at),
                    ("rotation" if mode == "direct" else "expected_orientation"): rotation,
                }
                if "can_step" in choices:
                    claims = {
                        "origin": [args["origin_x"], args["origin_y"]],
                        "can_step": args["can_step"],
                    }
                    if "marker_on_origin" in choices:
                        claims["marker_on_origin"] = args["marker_on_origin"]
                    checked_placement(
                        board,
                        tuple(state["goal"]),
                        marker,
                        state["hand"],
                        canonical | claims,
                    )
                    choice.update(claims)
    else:
        if name in ("propose_step", "stay"):
            dest = [args["x"], args["y"]] if name == "propose_step" else None
            require(
                dest is None or tuple(dest) in [tuple(p) for p in choices["to"] if p is not None],
                "choose a legal marker step",
            )
            choice = {"to": dest}
        elif name in ("pass_nomination", "nominate"):
            target = args.get("seat")
            require(target in choices["target"], "choose another living seat")
            choice = {"target": target}
        else:
            choice = {"vote": args["approve"]}
        canonical = choice
    return result, choice, canonical


def action_request(snapshot, model, tools, *, guided=False, task=None):
    state, choices, pieces = snapshot["state"], snapshot["choices"], snapshot["pieces"]
    body = model_request(snapshot, model)
    body["messages"][0]["content"] = RULES
    if snapshot.get("team_names") == "colors":
        color_brief(body)
    context = json.loads(body["messages"][1]["content"])
    del context["options"], context["hand"]
    context["held_pieces"] = [receipt(h, *piece) for h, piece in pieces.items()]
    if state["stage"] == "place":
        context["empty_build_squares"] = choices["at"]
        if guided:
            context["possible_forward_builds"] = [
                {
                    "piece": next(
                        h for h, (face, _) in pieces.items() if face == choices["tile"][e["tile"]]
                    ),
                    "rotation": choices["rotation"][e["rotation"]],
                    "at": choices["at"][e["at"]],
                }
                for e in forward_examples(snapshot)
            ]
        if "can_step" in choices:
            context.pop("origin_indices_by_at_index", None)
            context["origins"] = choices["origin"]
            context["required_check"] = (
                "Name an adjacent non-EXIT origin and say whether its outgoing edge and the rotated entrance permit a step from it to the new tile."
            )
    else:
        context["legal_values"] = choices
    if task:
        context["task"] = task
    body.pop("format")
    body["tools"] = tools
    body["think"] = False
    body["options"]["num_predict"] = 320
    body["messages"][0]["content"] += (
        " Act by calling one of the supplied functions. Give literal coordinates, piece handles and values. "
        "A committing call is your decision. Preparations are optional and private. "
        "A blocked or remote build is legal. Use one call at a time."
    )
    body["messages"][1]["content"] = json.dumps(context, separators=(",", ":"))
    return body


def native_decision(
    snapshot,
    model,
    seconds,
    *,
    mode,
    orient=None,
    trace=None,
    note_file=None,
    guided=False,
    task=None,
    max_calls=6,
    request_fn=request,
    prospects=False,
):
    """Return a transport choice on the first valid action. The host commits it once."""
    deadline = time.monotonic() + seconds
    require(mode in ("direct", "hand", "draft", "fit"), "unknown native action interface")
    tools = build_tools(snapshot, mode)
    specs = {t["function"]["name"]: t["function"]["parameters"]["properties"].copy() for t in tools}
    if note_file is not None:
        for t in tools:
            fn = t["function"]
            if fn["name"] not in PREPARATIONS:
                fn["parameters"]["properties"]["reason"] = {
                    "type": "string",
                    "description": "Optional short private reason for this choice.",
                }
    body = action_request(snapshot, model, tools, guided=guided, task=task)
    if mode == "draft" and snapshot["state"]["stage"] == "place":
        body["messages"][0]["content"] += (
            " Before committing, preview a candidate, then read its effect. You may change the "
            "piece orientation or try another square. commit_preview places exactly the last preview. "
            "Emit the native call directly. Keep time for the commit."
        )
    log = [] if trace is None else trace
    try:
        choice, canonical, reason = run_calls(
            snapshot,
            mode,
            tools,
            specs,
            body,
            deadline,
            max_calls,
            request_fn,
            orient,
            log,
            note_file is not None,
            prospects,
        )
    except (ValueError, OSError, HTTPException) as exc:
        if note_file is not None:
            save_note(note_file, snapshot, model, {}, f"No commit: {exc}", log)
        raise
    if note_file is not None:
        save_note(note_file, snapshot, model, canonical, reason, log)
    return choice


def run_calls(
    snapshot,
    mode,
    tools,
    specs,
    body,
    deadline,
    max_calls,
    request_fn,
    orient,
    log,
    explain,
    prospects,
):
    state, choices = snapshot["state"], snapshot["choices"]
    pieces = snapshot["pieces"].copy()
    draft = None
    for i in range(max_calls):
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError("native action deadline")
        if i == max_calls - 1:
            body["tools"] = [t for t in tools if t["function"]["name"] not in PREPARATIONS]
            body["messages"].append(
                {"role": "user", "content": "Last opportunity. Commit your decision now."}
            )
        response = request_fn(11434, "/api/chat", body, left)
        if time.monotonic() >= deadline:
            raise TimeoutError("late native action")
        require(isinstance(response, dict), "invalid model response")
        message = response.get("message")
        calls = message.get("tool_calls", []) if isinstance(message, dict) else []
        if not isinstance(calls, list) or len(calls) != 1 or not isinstance(calls[0], dict):
            status = (
                "truncated" if response.get("done_reason") == "length" else "expected-single-call"
            )
            log.append(
                {
                    "name": "selection",
                    "status": status,
                    "call_count": len(calls) if isinstance(calls, list) else None,
                }
            )
            body["messages"].append(
                {
                    "role": "user",
                    "content": "No action accepted. Send exactly one native function call.",
                }
            )
            continue
        fn = calls[0].get("function")
        name = fn.get("name") if isinstance(fn, dict) else None
        args = fn.get("arguments") if isinstance(fn, dict) else None
        event = {"name": name if isinstance(name, str) and name in specs else "unknown"}
        log.append(event)
        if mode == "draft" and name == "preview_placement":
            draft = None
        try:
            require(
                event["name"] != "unknown" and isinstance(args, dict),
                "unknown function or invalid arguments",
            )
            require(
                any(t["function"]["name"] == name for t in body["tools"]),
                "use a committing action now",
            )
            fields = specs[name]
            args = args.copy()
            reason = None
            if explain and name not in PREPARATIONS:
                reason = args.pop("reason", None)
                require(reason is None or isinstance(reason, str), "reason must be text")
            require(
                args.keys() == fields.keys()
                and all(
                    type(args[k]) is {"string": str, "integer": int, "boolean": bool}[f["type"]]
                    for k, f in fields.items()
                ),
                "use exactly the listed argument names and literal types",
            )
            event["arguments"] = args.copy()
            execute = name
            if name == "commit_preview":
                require(draft is not None, "preview a piece on a square first")
                handle, rotation, x, y = draft
                require(pieces[handle][1] == rotation, "orientation changed; preview again")
                execute = "place_tile"
                args = {**args, "piece": handle, "x": x, "y": y}
            result, choice, canonical = apply_call(
                execute, args, state, choices, pieces, mode, orient
            )
            if name == "preview_placement" and mode == "draft":
                draft = (args["piece"], result["rotation"], args["x"], args["y"])
                if prospects:
                    result.update(route_prospects(state, result))
            if name == "commit_preview":
                event["confirmed"] = {"piece": handle, "rotation": rotation, "x": x, "y": y}
            if choice is not None:
                event["status"] = "commit"
                return choice, canonical, reason
            event.update(status="ok", result=result)
        except ValueError as exc:
            result = {"error": str(exc)}
            event.update(status="rejected", result=result)
        body["messages"].extend(
            [
                {"role": "assistant", "content": "", "tool_calls": calls},
                {"role": "tool", "tool_name": event["name"], "content": json.dumps(result)},
            ]
        )
    raise ValueError("no valid commit within the native action allowance")
