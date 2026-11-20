"""Full-information JSON records and deterministic Markdown accounts."""

import json
from copy import deepcopy
from pathlib import Path

from .board import rotate
from .game import Game, require
from .team_names import COLORS

FORMAT = 1  # Default format with START implicit at the origin.
EXPLICIT_START_FORMAT = 2
RULES = "base-1"
FENCE = "\n```json footsteps-record\n"


def new_record(setup):
    version = EXPLICIT_START_FORMAT if "start" in setup else FORMAT
    return {"format": version, "rules": RULES, "setup": deepcopy(setup), "events": []}


def read(path):
    body = Path(path).read_text()
    if FENCE in body:
        # The importable record is the final labeled block: prose may quote
        # the block syntax earlier, so split at the last fence label.
        body, end, tail = body.rsplit(FENCE, 1)[1].partition("\n```")
        require(end and not tail.strip(), "malformed full account")
    return json.loads(body)


def describe(game, event, seat=None):
    kind = event["kind"]
    player = f"P{game.actor}"
    timed = " (timed out)" if event.get("timeout") else ""
    if timed and kind in ("place", "discard"):
        timed = " (random choice after timeout)"
    if kind == "draw":
        cards = event["tiles"]
        detail = f" {cards}" if seat == game.actor else ""
        noun = "tile" if len(cards) == 1 else "tiles"
        return f"{player} drew {len(cards)} {noun}{detail}."
    if kind == "place":
        face = rotate(event["tile"], event["rotation"])
        incoming, outgoing = [
            "/".join(name for d, name in enumerate("NESW") if mask & (1 << d)) or "none"
            for mask in (face & 15, face >> 4)
        ]
        return (
            f"{player} placed face {event['tile']} at {tuple(event['at'])}, "
            f"rotated {90 * event['rotation']}° clockwise (in: {incoming}, out: {outgoing}){timed}."
        )
    if kind == "discard":
        card = str(event["tile"]) if seat == game.actor else "a tile"
        return f"{player} returned {card} to the store{timed}."
    if kind == "propose":
        dest = event["to"]
        choice = "staying" if dest is None else f"moving to {tuple(dest)}"
        return f"{player} proposed {choice}{timed}."
    if kind == "nominate":
        who = game.queue[0]
        target = event["target"]
        choice = "passed" if target is None else f"nominated P{target}"
        return f"P{who} {choice}{timed}."
    labels = {True: "yes", False: "no", None: "timed out (no)"}
    votes = ", ".join(f"P{i} {labels[v]}" for i, v in zip(game.alive, event["votes"]))
    return f"{'Movement' if kind == 'move_vote' else 'Elimination'} ballots — {votes}."


def starting_game(record):
    require(
        type(record.get("format")) is int
        and record["format"] in (FORMAT, EXPLICIT_START_FORMAT)
        and record.get("rules") == RULES,
        "unsupported record format or rules version",
    )
    setup = record["setup"]
    if record["format"] == FORMAT:
        # Format 1 always started at the origin, even with extra setup metadata.
        setup = {k: v for k, v in setup.items() if k != "start"}
    else:
        require("start" in setup, "format 2 requires an explicit start")
    return Game(setup)


def replay(record, *, lines=None, seat=None):
    game = starting_game(record)
    require(isinstance(record["events"], list), "expected an event list")
    if lines is not None:
        labels = COLORS if record.get("team_names") == "colors" else {"good": "good", "bad": "bad"}
        lines.extend(
            [
                "# Footsteps game account",
                "",
                (
                    f"Players: {len(game.alive)} ({game.roles.count('bad')} {labels['bad']}). "
                    f"Start {game.marker}, goal {game.goal}, {len(game.store)} tiles in store."
                ),
            ]
        )
        if seat is not None:
            v = game.view(seat)
            lines += ["", f"P{seat} is {labels[v['role']]} and holds {v['hand']}."]
            if v["role"] == "bad":
                lines.append(f"Fellow {labels['bad']} players: {v['teammates']}.")
    for index, event in enumerate(record["events"]):
        try:
            if lines is not None:
                if game.stage == "draw":
                    lines += ["", f"## Turn {game.turn}", ""]
                statement = describe(game, event, seat)
                previous_alive = game.alive.copy()
            game.apply(event)
            if lines is not None:
                lines.append("- " + statement)
                if event["kind"] == "move_vote":
                    lines.append(f"- The marker is at {game.marker}.")
                if event["kind"] == "eliminate_vote":
                    lost = set(previous_alive) - set(game.alive)
                    lines.append(
                        f"- P{lost.pop()} was eliminated." if lost else "- The nomination failed."
                    )
        except (KeyError, ValueError, TypeError, IndexError, AttributeError) as e:
            raise ValueError(f"event {index + 1}: {e}") from e
    if lines is not None:
        lines += [
            "",
            f"Winner: **{labels[game.winner]}**."
            if game.winner
            else f"Next decision: **{game.stage}**.",
        ]
        if game.winner:
            lines.append(
                "Roles revealed: "
                + ", ".join(f"P{i} {labels[r]}" for i, r in enumerate(game.roles))
                + "."
            )
    return game


def render(record, seat=None, full=False):
    require(not full or seat is None, "full and seat views are mutually exclusive")
    lines = []
    replay(record, lines=lines, seat=seat)
    prose = "\n".join(lines) + "\n"
    if full:
        prose += "\n## Full referee record (includes all secrets)\n"
        prose += FENCE + json.dumps(record, indent=2) + "\n```\n"
    return prose
