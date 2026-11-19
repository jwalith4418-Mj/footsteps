"""Compile a record into a single offline, perspective-specific HTML transcript."""

import json
from pathlib import Path

from .game import Game
from .record import describe, replay

WEB = Path(__file__).with_name("web")


def transcript(record, seat=None, *, omniscient=False):
    if omniscient and seat is not None:
        raise ValueError("choose a seat or an omniscient view")
    # Validate before interpreting events for display (including the reported event index).
    replay(record)
    game = Game(record["setup"])
    setup = game.view(seat)
    frames = []

    def capture(kind, turn, message):
        view = game.view(seat)
        # The floor is write-once. Encode placements once and reconstruct their display by index.
        for key in ("board", "placements", "player_count", "bad_count", "goal"):
            del view[key]
        if omniscient:
            view["hands"] = [hand.copy() for hand in game.hands]
            view["roles"] = game.roles.copy()
        view["marker"] = tuple(map(str, view["marker"]))
        if view["stage"] == "move_vote":
            view["pending"] = tuple(map(str, view["pending"]))
        frame = {**view, "kind": kind, "event_turn": turn, "message": message}
        frames.append(frame)
        return frame

    capture("setup", 1, "The marker starts at (0, 0). The floor is ready for the first draw.")
    for event in record["events"]:
        kind, turn = event["kind"], game.turn
        message = describe(game, event, game.actor if omniscient else seat)
        ballots = list(zip(game.alive, event.get("votes", [])))
        marker, nominee = game.marker, game.pending
        game.apply(event)
        if kind == "move_vote":
            message = "Movement approved." if game.marker != marker else "Movement declined."
        elif kind == "eliminate_vote":
            message = (
                f"P{nominee} was eliminated." if nominee not in game.alive else "Nomination failed."
            )
        frame = capture(kind, turn, message)
        if kind == "place":
            p = tuple(event["at"])
            frame["placed"] = [tuple(map(str, p)), game.board[p], event["tile"], event["rotation"]]
        if ballots:
            frame["ballots"] = ballots

    return {
        "seat": seat,
        "omniscient": omniscient,
        "goal": tuple(map(str, setup["goal"])),
        "players": setup["player_count"],
        "bad": setup["bad_count"],
        "frames": frames,
    }


def export_html(record, title, seat=None, *, omniscient=False):
    data = transcript(record, seat, omniscient=omniscient)
    data["title"] = title
    payload = json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")
    return (
        (WEB / "viewer.html")
        .read_text()
        .replace("/* VIEWER_STYLE */", (WEB / "viewer.css").read_text())
        .replace("/* VIEWER_SCRIPT */", (WEB / "viewer.js").read_text())
        .replace("<!-- TRANSCRIPT -->", payload)
    )
