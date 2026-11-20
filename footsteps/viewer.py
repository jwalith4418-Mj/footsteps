"""Compile a record into a single offline, perspective-specific HTML transcript."""

import json
from pathlib import Path

from .decision_notes import applied_note, notes_for_record
from .game import Game, require
from .record import describe, replay
from .team_names import COLORS

WEB = Path(__file__).with_name("web")


def transcript(record, seat=None, *, omniscient=False, notes=()):
    if omniscient and seat is not None:
        raise ValueError("choose a seat or an omniscient view")
    if notes and not omniscient:
        raise ValueError("private decision notes require an omniscient export")
    grouped = notes_for_record(record, notes)
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
    for revision, event in enumerate(record["events"]):
        attached = [applied_note(game, event, row) for row in grouped.get(revision, [])]
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
        if attached:
            frame["decision_notes"] = attached
        if ballots:
            frame["ballots"] = ballots

    remarks = record.get("remarks", [])
    require(isinstance(remarks, list), "expected a list of public remarks")
    for remark in remarks:
        require(isinstance(remark, dict), "invalid public remark")
        revision, speaker, text = (remark.get(k) for k in ("after_event", "seat", "text"))
        if type(revision) is not int or not 0 <= revision < len(frames):
            raise ValueError("public remark outside this record")
        frame = frames[revision]
        if (
            frame["stage"] not in ("move_vote", "eliminate_vote")
            or type(speaker) is not int
            or speaker not in frame["alive"]
            or not isinstance(text, str)
            or not 0 < len(text.strip()) <= 500
        ):
            raise ValueError("invalid public ballot remark")
        frame.setdefault("remarks", []).append({"seat": speaker, "text": text})

    return {
        "seat": seat,
        "omniscient": omniscient,
        **({"team_labels": COLORS} if record.get("team_names") == "colors" else {}),
        "goal": tuple(map(str, setup["goal"])),
        "players": setup["player_count"],
        "bad": setup["bad_count"],
        "frames": frames,
    }


def export_html(record, title, seat=None, *, omniscient=False, notes=()):
    data = transcript(record, seat, omniscient=omniscient, notes=notes)
    data["title"] = title
    payload = json.dumps(data, separators=(",", ":")).replace("<", "\\u003c")
    return (
        (WEB / "viewer.html")
        .read_text()
        .replace("/* VIEWER_STYLE */", (WEB / "viewer.css").read_text())
        .replace("/* VIEWER_SCRIPT */", (WEB / "viewer.js").read_text())
        .replace("<!-- TRANSCRIPT -->", payload)
    )
