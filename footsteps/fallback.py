"""Resolve missed individual deadlines. Ballot collectors record a missing vote as None."""

from .board import frontier


def timeout(game, rng):
    stage = game.stage
    if stage in ("place", "discard"):
        face = rng.choice(sorted(set(game.hands[game.actor])))
        if stage == "place":
            at = rng.choice(frontier(game.board, game.goal))
            return {
                "kind": stage,
                "at": list(at),
                "tile": face,
                "rotation": rng.randrange(4),
                "timeout": True,
            }
        return {"kind": stage, "tile": face, "timeout": True}
    if stage == "propose":
        return {"kind": stage, "to": None, "timeout": True}
    if stage == "nominate":
        return {"kind": stage, "target": None, "timeout": True}
    raise ValueError(f"no individual decision is pending at {stage}")
