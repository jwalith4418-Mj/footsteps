"""Read-only queries against a single pending seat view."""

from .board import distance, moves, optimistic_length, rotate
from .solo import sealed


def spec_for(stage):
    if stage == "place":
        name = "preview_placement"
        desc = "Check a literal legal hand face, clockwise rotation and square. Returns legal moves after placing there and whether the marker is sealed."
        fields = {k: {"type": "integer"} for k in ("tile", "rotation", "x", "y")}
    elif stage in ("propose", "move_vote"):
        name = "compare_landings"
        desc = "Compare staying and the available moves, including permanent traps and the optimistic number of moves to EXIT."
        fields = {}
    else:
        return None
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": desc,
            "parameters": {
                "type": "object",
                "properties": fields,
                "required": list(fields),
                "additionalProperties": False,
            },
        },
    }


def query(snapshot, name, arguments):
    state = snapshot["state"]
    spec = spec_for(state["stage"])
    if spec is None or name != spec["function"]["name"] or not isinstance(arguments, dict):
        raise ValueError("unknown tool at this stage")
    expected = spec["function"]["parameters"]["properties"]
    if arguments.keys() != expected.keys() or any(type(v) is not int for v in arguments.values()):
        raise ValueError("invalid tool arguments")
    board = {tuple(p): face for p, face in state["board"]}
    marker, goal = tuple(state["marker"]), tuple(state["goal"])
    if name == "preview_placement":
        opts = snapshot["choices"]
        at = (arguments["x"], arguments["y"])
        face, rotation = arguments["tile"], arguments["rotation"]
        if (
            face not in opts["tile"]
            or rotation not in opts["rotation"]
            or at not in map(tuple, opts["at"])
        ):
            raise ValueError("placement is outside your legal menu")
        board[at] = rotate(face, rotation)
        return {
            "oriented_face": board[at],
            "destinations": moves(board, marker),
            "marker_permanently_sealed": sealed(board, marker, goal),
        }
    options = snapshot["choices"]["to"] if state["stage"] == "propose" else [None, state["pending"]]
    horizon = min(16, state["store_count"])
    landings = []
    for dest in options:
        pos = marker if dest is None else tuple(dest)
        landings.append(
            {
                "to": dest,
                "distance": distance(pos, goal),
                "at_exit": pos == goal,
                "permanently_sealed": sealed(board, pos, goal),
                "optimistic_steps": optimistic_length(board, pos, goal, horizon),
            }
        )
    return {
        "moves_after_this": state["store_count"],
        "search_horizon": horizon,
        "assumption": "All future tiles connect in every direction. Null means no route within the search horizon.",
        "landings": landings,
    }
