"""A local model plays through exactly one authenticated seat."""

import json
import time
from contextlib import closing
from http.client import HTTPConnection, HTTPException
from math import isfinite
from urllib.parse import urlsplit

from .action_language import action_brief, ballot_names
from .board import connects, distance, neighbors, rotate
from .decision_notes import REASON_PROMPT, request_reason, save_note
from .game import checked_placement
from .role_knowledge import role_information
from .seat_tools import query, spec_for
from .social import SOCIAL_STAGES, shortlist, social_request
from .solo import exits
from .team_names import COLORS, color_brief

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


def model_request(
    snapshot,
    model,
    *,
    guided=False,
    named_moves=False,
    named_ballots=False,
    explain=False,
    explicit_actions=False,
):
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
        **role_information(snapshot),
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
    if "can_step" in choices:
        instructions = (
            "Choose the zero-based tile, rotation, at and origin indices. Origin is an existing "
            "construction neighbor of at. For can_step, answer true or false: after rotation, "
            "can a marker hypothetically on origin step directly onto at? A blocked edge is legal "
            "to build. Placing leaves the actual marker on its current square."
        )
        context["origin_indices_by_at_index"] = [
            [i for i, p in enumerate(choices["origin"]) if tuple(p) in neighbors(at)]
            for at in choices["at"]
        ]
        schema["properties"]["can_step"] = {"type": "boolean"}
        if "marker_on_origin" in choices:
            instructions += (
                " For marker_on_origin, answer whether the actual marker is on origin now."
            )
            schema["properties"]["marker_on_origin"] = {"type": "boolean"}
    if named_moves and state["stage"] == "propose":
        directions = dict(zip(neighbors(state["marker"]), ("north", "east", "south", "west")))
        names = ["stay" if p is None else directions[tuple(p)] for p in choices["to"]]
        context["options"] = {"to": names}
        schema["properties"]["to"] = {"type": "string", "enum": names}
        instructions = "Choose one named action in options.to and return its name as the to field."
    if named_ballots and state["stage"] in ("move_vote", "eliminate_vote"):
        names = (
            ballot_names(state, choices["vote"])
            if explicit_actions
            else ["approve" if vote else "reject" for vote in choices["vote"]]
        )
        context["options"] = {"vote": names}
        schema["properties"]["vote"] = {"type": "string", "enum": names}
        instructions = (
            "Return the chosen action name as the vote field."
            if explicit_actions
            else "Choose approve to carry out the proposal or reject to decline it. Return its name as the vote field."
        )
    if explicit_actions:
        instructions += " " + action_brief(state)
    if explain:
        request_reason(schema)
        instructions += REASON_PROMPT
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
        "options": {
            "temperature": 0,
            "seed": 1,
            "num_ctx": 4096,
            "num_predict": 144 if explain else 64,
        },
    }


def consultation(snapshot, body, seconds):
    spec = spec_for(snapshot["state"]["stage"])
    if spec is None:
        return [], []
    probe = {k: v for k, v in body.items() if k != "format"}
    probe["tools"] = [spec]
    probe["think"] = False
    probe["messages"] = [
        {
            "role": "system",
            "content": "You can consult one listed Footsteps tool to inspect this decision before choosing. Use literal values from this seat's hand and floor. If you need no tool, return an empty object.",
        },
        body["messages"][1],
    ]
    probe["options"] = {**body["options"], "num_predict": 96}
    try:
        result = request(11434, "/api/chat", probe, seconds)
    except (OSError, HTTPException):
        return [], []
    message = result.get("message") if isinstance(result, dict) else None
    calls = message.get("tool_calls") if isinstance(message, dict) else None
    if not isinstance(calls, list) or not calls:
        return [], []
    call = calls[0]
    fn = call.get("function") if isinstance(call, dict) else None
    if not isinstance(fn, dict) or fn.get("name") != spec["function"]["name"]:
        return [], []
    name, args = fn["name"], fn.get("arguments")
    try:
        output = query(snapshot, name, args)
    except ValueError as exc:
        output = {"error": str(exc)}
    messages = [
        {"role": "assistant", "content": "", "tool_calls": [call]},
        {"role": "tool", "tool_name": name, "content": json.dumps(output, separators=(",", ":"))},
    ]
    return messages, [{"name": name, "ok": "error" not in output}]


def model_choice(body, choices, seconds, explain):
    answer = request(11434, "/api/chat", body, seconds)
    reply = json.loads(answer["message"]["content"])
    reason = reply.pop("reason", None) if explain and isinstance(reply, dict) else None
    if not isinstance(reply, dict) or reply.keys() != choices.keys():
        raise ValueError("model returned unexpected fields")
    choice = {}
    for key, values in choices.items():
        field = body["format"]["properties"][key]
        if field["type"] == "boolean":
            if type(reply[key]) is not bool:
                raise ValueError(f"{key} requires true or false")
            choice[key] = reply[key]
            continue
        i = field["enum"].index(reply[key]) if field["type"] == "string" else reply[key]
        if type(i) is not int or not 0 <= i < len(values):
            raise ValueError(f"model returned an invalid option index for {key}")
        choice[key] = values[i]
    return choice, reason


def edge_question(model, state, options, build, no_think):
    """Ask about an already selected, uncommitted build in literal floor coordinates."""
    dest = tuple(build["at"])
    board = {tuple(p): face for p, face in state["board"]}
    origins = [p for p in options["origin"] if tuple(p) in neighbors(dest)]
    names = [f"({p[0]},{p[1]})" for p in origins]
    fields = {"origin": {"type": "string", "enum": names}, "can_step": {"type": "boolean"}}
    inputs = {"origin": origins, "can_step": [True, False]}
    instructions = (
        "Check a proposed floor placement before it commits. Pick one listed origin by name. "
        "Read its outgoing side toward the new tile, then the rotated tile's entrance facing back. "
        "Set can_step true only if both sides allow that step. False is a valid build. "
        "Placement leaves the marker where it is."
    )
    if "marker_on_origin" in options:
        instructions += " Set marker_on_origin true only if your chosen origin equals the marker."
        fields["marker_on_origin"] = {"type": "boolean"}
        inputs["marker_on_origin"] = [True, False]
    context = {
        "marker": state["marker"],
        "new_square": dest,
        "rotated_tile_entrances": tile(rotate(build["tile"], build["rotation"]))[1],
        "origins": [
            {
                "name": name,
                "outgoing": tile(board[tuple(p)])[2],
                "direction_to_new_square": "NESW"[neighbors(p).index(dest)],
            }
            for p, name in zip(origins, names, strict=True)
        ],
    }
    body = {
        "model": model,
        "stream": False,
        "format": {
            "type": "object",
            "required": list(fields),
            "properties": fields,
            "additionalProperties": False,
        },
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps(context, separators=(",", ":"))},
        ],
        "options": {"temperature": 0, "seed": 1, "num_ctx": 4096, "num_predict": 64},
    }
    if no_think:
        body["think"] = False
    return body, inputs


def infer(
    snapshot,
    model,
    seconds,
    *,
    guided=False,
    named_moves=False,
    no_think=False,
    named_ballots=False,
    use_tools=False,
    explicit_actions=False,
    social_guidance=False,
    outcome_policy=False,
    note_file=None,
    placement_attempts=None,
    joint_placement=False,
):
    deadline = time.monotonic() + seconds
    social = (social_guidance or outcome_policy) and snapshot["state"]["stage"] in SOCIAL_STAGES
    if social and outcome_policy:
        key, legal = next(iter(snapshot["choices"].items()))
        eligible = shortlist(snapshot)
        if len(eligible) < len(legal):
            if len(eligible) == 1:
                choice = {key: eligible[0]}
                if note_file is not None:
                    save_note(
                        note_file,
                        snapshot,
                        "Footsteps outcome policy",
                        choice,
                        "Unique preferred team outcome if the action takes effect.",
                        [],
                    )
                return choice
            snapshot = {**snapshot, "choices": {key: eligible}}
    full_menu = snapshot["choices"]
    checked = "can_step" in full_menu
    separate = checked and not joint_placement
    if separate:
        snapshot = {**snapshot, "choices": {k: full_menu[k] for k in ("tile", "at", "rotation")}}
    body = model_request(
        snapshot,
        model,
        guided=guided,
        named_moves=named_moves,
        named_ballots=named_ballots,
        explain=note_file is not None,
        explicit_actions=explicit_actions,
    )
    if social:
        social_request(
            body,
            snapshot,
            explain=note_file is not None,
            human=outcome_policy,
            explicit_actions=explicit_actions,
        )
    if snapshot.get("team_names") == "colors":
        color_brief(body)
    if no_think:
        body["think"] = False
    used = []
    if use_tools:
        messages, used = consultation(snapshot, body, seconds / 2)
        body["messages"].extend(messages)
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError("tool consultation reached the decision deadline")
    options = snapshot["choices"]
    if not checked:
        choice, reason = model_choice(body, options, seconds, note_file is not None)
        if note_file is not None:
            save_note(note_file, snapshot, model, choice, reason, used)
        return choice

    state = snapshot["state"]
    board = {tuple(p): f for p, f in state["board"]}
    build = {}
    build_reason = None
    if separate:
        build, build_reason = model_choice(body, options, seconds, note_file is not None)
        body, options = edge_question(model, snapshot["state"], full_menu, build, no_think)
        seconds = deadline - time.monotonic()
        if seconds <= 0:
            raise TimeoutError("no time left to check the proposed placement")
    for attempt in range(2):
        choice = None
        try:
            choice, reason = model_choice(
                body, options, seconds, note_file is not None and not separate
            )
            choice = {**build, **choice}
            committed = checked_placement(
                board, tuple(state["goal"]), tuple(state["marker"]), state["hand"], choice
            )
        except ValueError as exc:
            if placement_attempts is not None:
                placement_attempts.append((choice, str(exc)))
            if attempt:
                raise
            body["messages"].append(
                {
                    "role": "user",
                    "content": (
                        f"Your placement {choice} was rejected: {exc} Submit a complete corrected choice "
                        "using the offered fields and literal booleans."
                    ),
                }
            )
            seconds = deadline - time.monotonic()
            if seconds <= 0:
                raise TimeoutError("placement correction reached the decision deadline") from exc
            continue
        if placement_attempts is not None:
            placement_attempts.append((choice, None))
        if note_file is not None:
            save_note(
                note_file, snapshot, model, committed, build_reason if separate else reason, used
            )
        return choice


def play_seat(seat, model, budget, *, decide=infer, report=print, request_note_id=False):
    if not isfinite(budget) or budget <= 0:
        raise ValueError("model budget must be positive")
    snapshot = seat.call("/ready", {"request_note_id": True} if request_note_id else {})
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
    winner = snapshot["state"]["winner"]
    label = COLORS[winner] if snapshot.get("team_names") == "colors" else winner.capitalize()
    report(f"{label} team wins.")
    return winner
