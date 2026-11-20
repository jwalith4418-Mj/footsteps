"""Deterministic referee. The caller supplies every chance outcome."""

from collections import Counter
from copy import deepcopy

from .board import OPEN, START, connects, frontier, moves, neighbors, rotate


def require(condition, message):
    if not condition:
        raise ValueError(message)


def integer(value):
    return type(value) is int


def point(value):
    require(
        isinstance(value, (list, tuple)) and len(value) == 2 and all(integer(v) for v in value),
        "expected integer coordinate pair",
    )
    return tuple(value)


def faces(values):
    require(
        isinstance(values, list) and all(integer(v) and 0 <= v < 256 for v in values),
        "expected a list of tile faces",
    )


def with_exit_origin(setup):
    """Express a fresh setup in coordinates measured from its EXIT."""
    gx, gy = point(setup["goal"])
    sx, sy = point(setup.get("start", START))
    return {**setup, "start": [sx - gx, sy - gy], "goal": [0, 0]}


def checked_placement(board, goal, marker, hand, choice):
    """Verify a builder's private edge claim, returning only the public placement."""
    origin, dest = point(choice["origin"]), point(choice["at"])
    tile, rotation = choice["tile"], choice["rotation"]
    require(origin in board, f"Origin {origin} has no floor tile.")
    require(origin != goal, "Choose START or an ordinary tile as the construction neighbor.")
    require(dest not in board, f"Placement square {dest} is occupied.")
    adjacent = neighbors(origin)
    require(dest in adjacent, f"Choose an origin sharing an edge with {dest}.")
    require(integer(tile) and tile in hand, "Choose a face in your hand.")
    require(integer(rotation) and 0 <= rotation < 4, "Choose a rotation from 0 to 3.")
    direction = adjacent.index(dest)
    target = rotate(tile, rotation)
    open_edge = connects(board[origin], target, direction)
    if type(choice["can_step"]) is not bool or choice["can_step"] != open_edge:
        outward = "open" if board[origin] & (16 << direction) else "closed"
        opposite = (direction + 2) % 4
        inward = "open" if target & (1 << opposite) else "closed"
        raise ValueError(
            f"From {origin} the {'NESW'[direction]} outgoing side is {outward}. "
            f"At {dest} the rotated tile's {'NESW'[opposite]} entrance is {inward}. "
            f"The step is {'legal' if open_edge else 'blocked'}. The marker remains at {marker}."
        )
    if "marker_on_origin" in choice:
        require(
            type(choice["marker_on_origin"]) is bool
            and choice["marker_on_origin"] == (origin == marker),
            f"The marker is at {marker}. Compare that square with your origin {origin}.",
        )
    return {"tile": tile, "rotation": rotation, "at": list(dest)}


class Game:
    def __init__(self, setup):
        setup = deepcopy(setup)
        self.goal = point(setup["goal"])
        self.start = point(setup.get("start", START))
        require(self.goal != self.start, "start and goal must differ")
        self.board = {self.start: OPEN, self.goal: OPEN}
        self.placements = {}
        self.marker = self.start
        self.roles = setup["roles"]
        self.hands = setup["hands"]
        self.store = setup["store"]
        require(
            isinstance(self.roles, list)
            and "good" in self.roles
            and all(r in ("good", "bad") for r in self.roles),
            "invalid teams",
        )
        require(
            isinstance(self.hands, list) and len(self.hands) == len(self.roles),
            "one hand per player",
        )
        for hand in self.hands:
            faces(hand)
        require(len({len(h) for h in self.hands}) == 1, "unequal starting hands")
        faces(self.store)
        require(self.store, "at least one tile must remain after dealing")
        self.alive = list(range(len(self.roles)))
        self.actor = 0
        self.turn = 1
        self.stage = "draw"
        self.winner = None
        self.pending = None
        self.queue = []
        self.last_draw = 0

    def apply(self, event):
        """Validate a realized event before committing its effects."""
        require(self.stage != "over" and event["kind"] == self.stage, "unexpected event")
        kind = self.stage
        fields = {
            "draw": {"tiles"},
            "place": {"tile", "at", "rotation"},
            "discard": {"tile"},
            "propose": {"to"},
            "move_vote": {"votes"},
            "nominate": {"target"},
            "eliminate_vote": {"votes"},
        }[kind]
        optional = {"timeout"} if kind in ("place", "discard", "propose", "nominate") else set()
        require(
            fields | {"kind"} <= event.keys() <= fields | {"kind"} | optional,
            "unexpected or missing event field",
        )
        require(type(event.get("timeout", False)) is bool, "invalid timeout marker")
        hand = self.hands[self.actor]
        if kind == "draw":
            drawn = event["tiles"]
            faces(drawn)
            require(
                len(drawn) == min(2, len(self.store))
                and not (Counter(drawn) - Counter(self.store)),
                "invalid draw",
            )
            for tile in drawn:
                self.store.remove(tile)
            hand.extend(drawn)
            self.last_draw = len(drawn)
            self.stage = "place"
        elif kind == "place":
            tile, rotation, at = event["tile"], event["rotation"], point(event["at"])
            require(
                integer(tile) and tile in hand and integer(rotation) and 0 <= rotation < 4,
                "invalid tile or rotation",
            )
            require(at in frontier(self.board, self.goal), "illegal placement square")
            self.placements[at] = (tile, rotation)
            self.board[at] = rotate(tile, rotation)
            hand.remove(tile)
            self.stage = "discard" if self.last_draw == 2 else "propose"
        elif kind == "discard":
            tile = event["tile"]
            require(integer(tile) and tile in hand, "discard must be in hand")
            hand.remove(tile)
            self.store.append(tile)
            self.stage = "propose"
        elif kind == "propose":
            dest = event["to"]
            if dest is None:
                self.after_movement()
            else:
                dest = point(dest)
                require(
                    not event.get("timeout") and dest in moves(self.board, self.marker),
                    "illegal proposed movement",
                )
                self.pending = dest
                self.stage = "move_vote"
        elif kind in ("move_vote", "eliminate_vote"):
            ballots = event["votes"]
            require(
                isinstance(ballots, list)
                and len(ballots) == len(self.alive)
                and all(v is None or type(v) is bool for v in ballots),
                "invalid ballots",
            )
            margin = 2 * ballots.count(True) - len(ballots)
            if kind == "move_vote":
                if margin > 0 or (margin == 0 and ballots[self.alive.index(self.actor)] is True):
                    self.marker = self.pending
                self.pending = None
                self.after_movement()
            else:
                if margin > 0:
                    self.alive.remove(self.pending)
                self.pending = None
                if all(self.roles[i] == "bad" for i in self.alive):
                    self.finish("bad")
                else:
                    self.advance_nomination()
        elif kind == "nominate":
            target = event["target"]
            if target is None:
                self.queue.pop(0)
                self.advance_nomination()
            else:
                require(
                    not event.get("timeout")
                    and integer(target)
                    and target in self.alive
                    and target != self.queue[0],
                    "illegal nominee",
                )
                self.pending = target
                self.queue.pop(0)
                self.stage = "eliminate_vote"

    def after_movement(self):
        if self.marker == self.goal:
            self.finish("good")
        elif not self.store:
            self.finish("bad")
        else:
            self.queue = [i for i in self.alive if i > self.actor]
            self.queue += [i for i in self.alive if i <= self.actor]
            self.advance_nomination()

    def advance_nomination(self):
        self.queue = [i for i in self.queue if i in self.alive]
        if self.queue and len(self.alive) > 1:
            self.stage = "nominate"
        else:
            self.queue = []
            self.actor = next((i for i in self.alive if i > self.actor), self.alive[0])
            self.turn += 1
            self.stage = "draw"

    def finish(self, winner):
        self.winner = winner
        self.stage = "over"

    def view(self, seat=None):
        """Fresh public snapshot, optionally including one player's private information."""
        v = {
            "start": self.start,
            "goal": self.goal,
            "marker": self.marker,
            "actor": self.actor,
            "turn": self.turn,
            "stage": self.stage,
            "winner": self.winner,
            "alive": self.alive.copy(),
            "player_count": len(self.roles),
            "bad_count": self.roles.count("bad"),
            "store_count": len(self.store),
            "pending": self.pending,
            "nominator": self.queue[0] if self.stage == "nominate" else None,
            "board": sorted(self.board.items()),
            "placements": sorted(self.placements.items()),
        }
        if self.winner:
            v["roles"] = self.roles.copy()
        if seat is not None:
            require(integer(seat) and 0 <= seat < len(self.roles), "invalid seat")
            v.update(hand=self.hands[seat].copy(), role=self.roles[seat])
            if self.roles[seat] == "bad":
                v["teammates"] = [
                    i for i, role in enumerate(self.roles) if role == "bad" and i != seat
                ]
        return v
