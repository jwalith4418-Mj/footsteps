"""Solitaire players. Policies see only the board, marker, goal and available hand."""

from collections import deque
from random import Random

from .board import connects, distance, frontier, moves, neighbors, rotate
from .game import Game
from .record import new_record

POLICIES = ("random", "greedy", "exits", "switch", "route")


def setup(seed, goal, size, store, density):
    rng = Random(seed)
    tiles = [
        sum(1 << bit for bit in range(8) if rng.random() < density) for _ in range(size + store)
    ]
    return {"goal": list(goal), "hands": [tiles[:size]], "store": tiles[size:], "roles": ["blue"]}


def best(choices, score, rng):
    winners = []
    highest = None
    for choice in choices:
        value = score(choice)
        if highest is None or value > highest:
            highest = value
            winners = [choice]
        elif value == highest:
            winners.append(choice)
    return rng.choice(winners)


def exits(board, p, tile, goal):
    """Score a destination by the best usable exit, including unbuilt squares."""
    if p == goal:
        return 3
    result = 0
    for d, q in enumerate(neighbors(p)):
        if tile & (16 << d) and (q not in board or connects(tile, board[q], d)):
            result = max(result, 2 if distance(q, goal) < distance(p, goal) else 1)
    return result


def reachable(board, marker):
    """For each reachable square, yield travel time and the first step of a shortest path."""
    queue = deque([(marker, 0, marker)])
    seen = {marker}
    while queue:
        p, steps, first = queue.popleft()
        yield p, steps, first
        for q in moves(board, p):
            if q not in seen:
                seen.add(q)
                queue.append((q, steps + 1, q if steps == 0 else first))


def route_placements(board, marker, goal, faces, rotations=range(4)):
    for origin, steps, _ in reachable(board, marker):
        if origin == goal:
            continue
        for d, p in enumerate(neighbors(origin)):
            if p in board or not board[origin] & (16 << d):
                continue
            for face in faces:
                for r in rotations:
                    tile = rotate(face, r)
                    if connects(board[origin], tile, d):
                        onward = exits(board, p, tile, goal)
                        score = (onward > 0, -steps - distance(p, goal), onward)
                        yield score, (p, face, r)


def route_move(board, marker, goal, rng):
    paths = []
    for origin, steps, first in reachable(board, marker):
        if origin == goal:
            return first
        for d, p in enumerate(neighbors(origin)):
            if p not in board and board[origin] & (16 << d):
                paths.append((steps + 1 + distance(p, goal), first))
    if not paths:
        return marker
    return best(paths, lambda path: -path[0], rng)[1]


def placement(board, marker, goal, hand, policy, rng, *, rotations=range(4)):
    squares = frontier(board, goal)
    faces = sorted(set(hand))
    if policy == "route":
        options = list(route_placements(board, marker, goal, faces, rotations))
        if options:
            return best(options, lambda option: option[0], rng)[1]
    elif policy != "random":
        candidates = [
            (p, t, r)
            for d, p in enumerate(neighbors(marker))
            if p in squares
            for t in faces
            for r in rotations
            if connects(board[marker], rotate(t, r), d)
        ]
        if candidates:

            def score(option):
                p, tile, r = option
                if policy == "greedy":
                    return -distance(p, goal)
                onward = exits(board, p, rotate(tile, r), goal)
                return (onward > 0, -distance(p, goal), onward)

            return best(candidates, score, rng)
    return rng.choice(squares), rng.choice(faces), rng.choice(rotations)


def movement(board, marker, goal, policy, rng):
    if policy == "route":
        return route_move(board, marker, goal, rng)
    options = [marker] + moves(board, marker)
    if policy == "random":
        return rng.choice(options)

    def score(p):
        if policy == "greedy":
            return -distance(p, goal)
        onward = exits(board, p, board[p], goal)
        return (p == goal, onward > 0, -distance(p, goal), onward)

    return best(options, score, rng)


def sealed(board, marker, goal):
    """Certify a trap if the reachable component excludes goal and any open frontier exit."""
    seen = {marker}
    work = [marker]
    while work:
        p = work.pop()
        if p == goal:
            return False
        for d, q in enumerate(neighbors(p)):
            if q not in board and board[p] & (16 << d):
                return False
        for q in moves(board, p):
            if q not in seen:
                seen.add(q)
                work.append(q)
    return True


def simulate(initial, seed, policy, capture=False):
    if policy not in POLICIES:
        raise ValueError(f"unknown policy {policy}")
    draw_rng = Random(f"draw/{seed}")
    rng = Random(f"choices/{seed}")
    game = Game(initial)
    rec = new_record(initial) if capture else None

    def act(kind, **fields):
        e = dict(kind=kind, **fields)
        game.apply(e)
        if capture:
            rec["events"].append(e)

    near = None
    while not game.winner:
        if near is None and distance(game.marker, game.goal) <= 2:
            near = game.turn
        current = policy
        if policy == "switch":
            current = "greedy" if near is None else "exits"
        drawn = draw_rng.sample(game.store, k=min(2, len(game.store)))
        act("draw", tiles=drawn)
        hand = game.hands[0]
        at, tile, rotation = placement(game.board, game.marker, game.goal, hand, current, rng)
        act("place", at=list(at), tile=tile, rotation=rotation)
        if game.stage == "discard":
            faces = sorted(set(hand))
            discard = (
                rng.choice(faces)
                if current == "random"
                else best(faces, lambda face: -face.bit_count(), rng)
            )
            act("discard", tile=discard)
        dest = movement(game.board, game.marker, game.goal, current, rng)
        act("propose", to=None if dest == game.marker else list(dest))
        if game.stage == "move_vote":
            act("move_vote", votes=[True])
    result = {
        "policy": policy,
        "seed": seed,
        "win": int(game.winner == "blue"),
        "turns": game.turn,
        "remaining": len(game.store),
        "sealed": int(sealed(game.board, game.marker, game.goal)),
        "end_distance": distance(game.marker, game.goal),
        "near_turn": near,
    }
    return result, rec
