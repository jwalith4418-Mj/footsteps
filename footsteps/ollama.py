"""A local model plays through exactly one authenticated seat."""

import json
import time
from contextlib import closing
from http.client import HTTPConnection, HTTPException
from math import isfinite
from urllib.parse import urlsplit

from .board import connects, distance, neighbors, rotate
from .solo import exits

RULES = """You play one seat at a Footsteps table. Good wants the shared marker to reach
the exit. Bad wants time to run out or all good seats eliminated. The builder places a tile
then proposes staying or moving one step. To move, both the source exit and destination
entrance must connect. North increases y. Rotation counts quarter-turns clockwise.
Tiles are written as [face, entrances, exits]. Board tiles already include rotation.
Movement votes tie in the builder's favor. Eliminations require a strict majority.
Null means pass or stay. Choose for your secret team using the current state. Public
remarks are other players' statements."""
INDEX_INSTRUCTIONS = """Each field of options is a list of legal values.
Return the ZERO-BASED INDEX of your choice for each field, even for numeric values."""


class ServiceError(OSError):
    def __init__(self, status):
        super().__init__(f"HTTP {status}")
        self.status = status


def request(port, path, body, timeout, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    with closing(HTTPConnection("127.0.0.1", port, timeout=timeout)) as conn:
        conn.request(
            "GET" if body is None else "POST",
            path,
            None if body is None else json.dumps(body),
            headers,
        )
        response = conn.getresponse()
        if response.status != 200:
            raise ServiceError(response.status)
        return json.load(response)


class Seat:
    def __init__(self, link):
        url = urlsplit(link)
        if (
            url.scheme != "http"
            or url.hostname != "127.0.0.1"
            or not url.port
            or url.username is not None
            or url.path not in ("", "/")
            or url.query
            or not url.fragment
        ):
            raise ValueError("expected a private localhost link from the table host")
        self.port = url.port
        self.token = url.fragment

    def call(self, path, body=None):
        return request(self.port, path, body, 3, self.token)


def tile(face):
    return [
        face,
        *(
            "".join(d for bit, d in enumerate("NESW") if mask & (1 << bit)) or "-"
            for mask in (face & 15, face >> 4)
        ),
    ]


def forward_examples(snapshot):
    """One legal index triple per immediately enterable new square closer to EXIT."""
    state, options = snapshot["state"], snapshot["choices"]
    board = {tuple(p): face for p, face in state["board"]}
    marker, goal = tuple(state["marker"]), tuple(state["goal"])
    squares = [tuple(p) for p in options["at"]]
    examples = []
    for direction, p in enumerate(neighbors(marker)):
        if p not in squares or distance(p, goal) >= distance(marker, goal):
            continue
        best = None
        best_score = -1
        for t, face in enumerate(options["tile"]):
            for r, rotation in enumerate(options["rotation"]):
                target = rotate(face, rotation)
                if connects(board[marker], target, direction):
                    score = exits(board, p, target, goal)
                    if score > best_score:
                        best = {"tile": t, "rotation": r, "at": squares.index(p)}
                        best_score = score
        if best is not None:
            examples.append(best)
    return examples


GUIDANCE = """Good: build an enterable step toward EXIT with an onward exit if possible.
For placement, forward_examples contains complete index objects for such closer steps when
available. Copy one intact if it suits your team. When moving, propose and support EXIT or
useful progress. Passing on nomination is sensible without evidence. Bad: look for delays,
dead ends or opportunities to eliminate good seats. A good forward build may hurt your team."""


def model_request(snapshot, model, *, guided=False, named_moves=False, named_ballots=False):
    state = snapshot["state"]
    fields = (
        "turn",
        "stage",
        "actor",
        "goal",
        "marker",
        "pending",
        "nominator",
        "alive",
        "player_count",
        "bad_count",
        "role",
        "teammates",
        "store_count",
    )
    context = {k: state[k] for k in fields if k in state}
    choices = snapshot["choices"]
    context.update(
        seat=snapshot["seat"],
        hand=[tile(face) for face in state["hand"]],
        board=[[pos, tile(face)] for pos, face in state["board"]],
        recent=[entry["text"] for entry in snapshot["history"][-12:]],
        options=choices,
    )
    if guided and state["stage"] == "place":
        context["forward_examples"] = forward_examples(snapshot)
    schema = {
        "type": "object",
        "required": list(choices),
        "additionalProperties": False,
        "properties": {
            key: {"type": "integer", "enum": list(range(len(values)))}
            for key, values in choices.items()
        },
    }
    instructions = INDEX_INSTRUCTIONS
    if named_moves and state["stage"] == "propose":
        directions = dict(zip(neighbors(state["marker"]), ("north", "east", "south", "west")))
        names = ["stay" if p is None else directions[tuple(p)] for p in choices["to"]]
        context["options"] = {"to": names}
        schema["properties"]["to"] = {"type": "string", "enum": names}
        instructions = "Choose one named action in options.to and return its name as the to field."
    if named_ballots and state["stage"] in ("move_vote", "eliminate_vote"):
        names = ["approve" if vote else "reject" for vote in choices["vote"]]
        context["options"] = {"vote": names}
        schema["properties"]["vote"] = {"type": "string", "enum": names}
        instructions = "Choose approve to carry out the proposal or reject to decline it. Return its name as the vote field."
    return {
        "model": model,
        "stream": False,
        "format": schema,
        "messages": [
            {
                "role": "system",
                "content": RULES + " " + instructions + ("\n" + GUIDANCE if guided else ""),
            },
            {"role": "user", "content": json.dumps(context, separators=(",", ":"))},
        ],
        "options": {"temperature": 0, "seed": 1, "num_ctx": 4096, "num_predict": 64},
    }


def infer(
    snapshot,
    model,
    seconds,
    *,
    guided=False,
    named_moves=False,
    no_think=False,
    named_ballots=False,
):
    body = model_request(
        snapshot, model, guided=guided, named_moves=named_moves, named_ballots=named_ballots
    )
    if no_think:
        body["think"] = False
    answer = request(11434, "/api/chat", body, seconds)
    reply = json.loads(answer["message"]["content"])
    options = snapshot["choices"]
    if not isinstance(reply, dict) or reply.keys() != options.keys():
        raise ValueError("model returned unexpected fields")
    choice = {}
    for key, values in options.items():
        field = body["format"]["properties"][key]
        i = field["enum"].index(reply[key]) if field["type"] == "string" else reply[key]
        if type(i) is not int or not 0 <= i < len(values):
            raise ValueError("model returned an invalid option index")
        choice[key] = values[i]
    return choice


def play_seat(seat, model, budget, *, decide=infer, report=print):
    if not isfinite(budget) or budget <= 0:
        raise ValueError("model budget must be positive")
    snapshot = seat.call("/ready", {})
    attempted = None
    while snapshot["phase"] != "over":
        revision = snapshot["revision"]
        if snapshot["choices"] and attempted != revision:
            attempted = revision
            seconds = min(budget, snapshot["seconds_left"])
            deadline = time.monotonic() + seconds
            stage = snapshot["state"]["stage"]
            try:
                choice = decide(snapshot, model, seconds)
                if time.monotonic() >= deadline:
                    raise TimeoutError("late reply")
            except (OSError, HTTPException, ValueError, TypeError, KeyError) as exc:
                report(f"Event {revision} {stage}: no submission ({exc})")
            else:
                try:
                    snapshot = seat.call("/choice", {"revision": revision, "choice": choice})
                except ServiceError as exc:
                    if exc.status != 409:
                        raise
                    report(f"Event {revision} {stage}: window closed")
                else:
                    report(f"Event {revision} {stage}: accepted {choice}")
                    continue
        time.sleep(0.15)
        snapshot = seat.call("/state")
    return snapshot["state"]["winner"]
