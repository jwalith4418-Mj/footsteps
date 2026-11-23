"""A private JSONL sidecar containing model statements about attempted actions."""

import json
import os
import warnings
from pathlib import Path
from tempfile import NamedTemporaryFile

REASON_PROMPT = (
    " Include one short sentence in reason citing a specific observation relevant to your choice."
)


def request_reason(schema):
    schema["properties"]["reason"] = {"type": "string", "maxLength": 240}
    schema["required"].append("reason")


def save_note(file, snapshot, model, choice, reason, used):
    state = snapshot["state"]
    row = {
        "version": 1,
        "table_id": snapshot.get("table_id"),
        "seat": snapshot["seat"],
        "revision": snapshot["revision"],
        "turn": state["turn"],
        "stage": state["stage"],
        "model": model,
        "choice": choice,
        "tools": used,
        "reason": reason.strip()[:240] if isinstance(reason, str) else None,
    }
    write_private_row(file, row)


def write_private_row(file, row):
    try:
        file.write(json.dumps(row, separators=(",", ":")) + "\n")
        file.flush()
    except OSError:
        warnings.warn("Could not save the private decision note.", RuntimeWarning, stacklevel=2)


def open_private(path):
    return open(path, "x", encoding="utf-8", opener=lambda p, flags: os.open(p, flags, 0o600))


def save_private_export(path, html):
    with NamedTemporaryFile(dir=path.parent, mode="w", encoding="utf-8", delete=False) as handle:
        temp = Path(handle.name)
        try:
            handle.write(html)
            handle.flush()
            os.replace(temp, path)
        finally:
            temp.unlink(missing_ok=True)


def read_notes(paths):
    rows = []
    for path in paths:
        with path.open(encoding="utf-8") as source:
            for index, line in enumerate(source, 1):
                try:
                    row = json.loads(line)
                    if not isinstance(row, dict):
                        raise TypeError("expected an object")
                    rows.append(row)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"{path}, line {index}: {exc}") from exc
    return rows


def notes_for_record(record, notes):
    grouped = {}
    for row in notes:
        if (
            row.get("version") != 1
            or not record.get("table_id")
            or row.get("table_id") != record["table_id"]
        ):
            raise ValueError("decision note version or table ID does not match this record")
        rev = row.get("revision")
        rotation = row.get("kind") == "hand_rotation"
        thinking = row.get("kind") == "thinking"
        if type(rev) is not int or not 0 <= rev < len(record["events"]) + int(rotation or thinking):
            raise ValueError("decision note refers to an event outside this record")
        if thinking:
            if type(row.get("seat")) is not int or not all(
                isinstance(row.get(k), str) for k in ("model", "label", "thinking")
            ):
                raise ValueError("invalid private thinking trace")
            grouped.setdefault(rev, []).append(row)
            continue
        if rotation:
            if not (
                type(row.get("seat")) is int
                and isinstance(row.get("piece"), str)
                and row["piece"].startswith("H")
                and row["piece"][1:].isascii()
                and row["piece"][1:].isdigit()
                and type(row.get("face")) is int
                and 0 <= row["face"] < 256
                and all(type(row.get(k)) is int and 0 <= row[k] < 4 for k in ("from", "to"))
            ):
                raise ValueError("invalid private hand rotation")
            grouped.setdefault(rev, []).append(row)
            continue
        if (
            type(row.get("seat")) is not int
            or not isinstance(row.get("model"), str)
            or not isinstance(row.get("choice"), dict)
        ):
            raise ValueError("invalid decision note fields")
        if row.get("reason") is not None and not isinstance(row["reason"], str):
            raise ValueError("invalid decision note reason")
        grouped.setdefault(rev, []).append(row)
    return grouped


def tool_receipt(tool):
    row = {k: tool[k] for k in ("name", "ok", "status", "tile") if k in tool}
    args = tool.get("arguments")
    if isinstance(args, dict):
        if isinstance(args.get("piece"), str):
            row["piece"] = args["piece"][:32]
        if type(args.get("x")) is int and type(args.get("y")) is int:
            row["at"] = [args["x"], args["y"]]
        if type(args.get("rotation")) is int:
            row["rotation"] = args["rotation"]
    result = tool.get("result")
    if isinstance(result, dict):
        if type(result.get("face")) is int:
            row["tile"] = result["face"]
        if type(result.get("can_step_here")) is bool:
            row["can_step_here"] = result["can_step_here"]
    return row


def applied_note(game, event, row):
    seat = row["seat"]
    stage = game.stage
    if row.get("stage") != stage or row.get("turn") != game.turn or seat not in game.alive:
        raise ValueError("decision note does not match the turn, stage or living seat")
    if stage in ("move_vote", "eliminate_vote"):
        actual = {"vote": event["votes"][game.alive.index(seat)]}
    else:
        actor = game.queue[0] if stage == "nominate" else game.actor
        if stage == "draw" or actor != seat:
            raise ValueError("decision note does not match the acting seat")
        actual = {k: v for k, v in event.items() if k not in ("kind", "timeout")}
    # Only project the tool receipt fields. Sidecars can have additional private metadata.
    tools = (
        [
            tool_receipt(tool)
            for tool in row.get("tools", [])
            if isinstance(tool, dict) and isinstance(tool.get("name"), str)
        ]
        if isinstance(row.get("tools"), list)
        else []
    )
    return {
        **({"tools": tools} if tools else {}),
        "seat": seat,
        "model": row["model"],
        "reason": row.get("reason"),
        "choice": row["choice"],
        "matches": actual != {"vote": None}
        and not event.get("timeout")
        and json.dumps(actual, sort_keys=True) == json.dumps(row["choice"], sort_keys=True),
    }
