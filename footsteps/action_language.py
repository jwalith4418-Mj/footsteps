"""Player-facing descriptions of what a single decision changes."""


def square(pos):
    return f"({pos[0]},{pos[1]})"


def action_brief(state):
    marker = square(state["marker"])
    stage = state["stage"]
    if stage == "place":
        return f"Place one floor tile. The marker remains at {marker}. You may later propose a step onto any connected adjacent tile, including an older one."
    if stage == "discard":
        return f"Return a hand tile to the bag. The placed tile stays on the floor and the marker remains at {marker}."
    if stage == "propose":
        return f"The tile is already placed. Choose stay at {marker} or propose one step for the shared marker. Stay resolves now. A proposed step needs a movement ballot."
    if stage == "move_vote":
        return f"Movement ballot. Vote on moving the marker from {marker} to {square(state['pending'])}. If the step is rejected the marker stays. A tie uses the builder's own vote."
    if stage == "nominate":
        return f"Name another player for a removal ballot, or pass on this nomination. Naming a player opens a ballot. The floor and marker at {marker} stay as they are."
    if stage == "eliminate_vote":
        return f"Removal ballot about P{state['pending']}. A strict majority removes that player; a tie keeps them in play. The marker remains at {marker} either way."
    return ""


def ballot_names(state, votes):
    if state["stage"] == "move_vote":
        yes = "step_to_" + "_".join(map(str, state["pending"]))
        no = "remain_at_" + "_".join(map(str, state["marker"]))
    else:
        yes, no = f"remove_P{state['pending']}", f"keep_P{state['pending']}"
    return [yes if vote else no for vote in votes]
