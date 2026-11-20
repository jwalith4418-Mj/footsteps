"""Read-only queries against a single pending seat view."""

from .board import distance, frontier, moves, neighbors, optimistic_length, rotate
from .solo import sealed


def spec_for(stage):
    if stage == "place":
        name = "preview_placement"
        desc = "Check a literal legal hand face, clockwise rotation and square. Returns possible marker steps after this placement, whether it seals the marker, and any held placement that blocks its last open side."
        fields = {k: {"type": "integer"} for k in ("tile", "rotation", "x", "y")}
    elif stage in ("propose", "move_vote"):
        name = "compare_landings"
        desc = "Compare staying and the available moves, including permanent traps and the optimistic number of moves to EXIT. If you build next, check whether a held tile can block the landing immediately."
        fields = {}
    elif stage in ("nominate", "eliminate_vote"):
        name = "check_builder_turns"
        desc = "Check one seat's completed builds, proposed steps and actual marker motion in the public referee history. Supply their numeric seat ID."
        fields = {"builder": {"type": "integer"}}
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
    if name == "check_builder_turns":
        builder = arguments["builder"]
        if not 0 <= builder < state["player_count"]:
            raise ValueError("unknown builder seat")
        if "floor_turns" not in snapshot:
            raise ValueError("public floor history unavailable")
        rows = [row for row in snapshot["floor_turns"] if row["builder"] == builder]
        return {"builder": builder, "completed_floor_turns": len(rows), "latest_four": rows[-4:]}
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
        block = blocking_tile(board, marker, goal, state["hand"])
        board[at] = rotate(face, rotation)
        return {
            "oriented_face": board[at],
            "own_hand_immediate_block_on_original_floor": block,
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
    if state.get("alive") and state["store_count"] > 0:
        alive = state["alive"]
        next_builder = alive[(alive.index(state["actor"]) + 1) % len(alive)]
        for landing in landings:
            landing["next_builder_if_all_survive"] = next_builder
            if next_builder == snapshot["seat"] and not landing["at_exit"]:
                dest = marker if landing["to"] is None else tuple(landing["to"])
                landing["own_hand_immediate_block"] = blocking_tile(
                    board, dest, goal, state["hand"]
                )
    return {
        "moves_after_this": state["store_count"],
        "search_horizon": horizon,
        "assumption": "All future tiles connect in every direction. Null means no route within the search horizon.",
        "landings": landings,
    }


def blocking_tile(board, pos, goal, hand):
    """Witness for blocking every immediate exit with one held tile at the next build."""
    if moves(board, pos):
        return None
    openings = [
        p for d, p in enumerate(neighbors(pos)) if board[pos] & (16 << d) and p not in board
    ]
    if len(openings) != 1 or openings[0] not in frontier(board, goal):
        return None
    at = openings[0]
    for tile in hand:
        for rotation in range(4):
            if not moves({**board, at: rotate(tile, rotation)}, pos):
                return {"tile": tile, "rotation": rotation, "at": at}
    return None
