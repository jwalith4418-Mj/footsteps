"""Single live table. The transport serializes calls and supplies a monotonic clock."""

from copy import copy
from math import isfinite

from .board import frontier, moves
from .fallback import timeout
from .game import Game, checked_placement, require
from .record import describe, new_record

# Print order in playtest/kit.typ. Equal faces are separate physical pieces.
PAPER_KIT = (188, 153, 16, 71, 45, 91, 121, 41, 234, 12, 44, 16, 74, 107, 41, 182)
BALLOTS = {"move_vote", "eliminate_vote"}


def fixed_kit(rng, size, entrances, exits):
    """Choose uniform subsets of labelled tile sides, independently for each direction of travel."""
    require(type(size) is int and size >= 1, "kit size must be positive")
    slots = 4 * size
    faces = [0] * size
    for count, shift in ((entrances, 0), (exits, 4)):
        require(type(count) is int and 0 <= count <= slots, f"kit counts must be in 0..{slots}")
        order = list(range(slots))
        rng.shuffle(order)
        for slot in order[:count]:
            faces[slot // 4] |= 1 << (shift + slot % 4)
    return tuple(faces)


def paper_setup(rng, seats=4, *, kit=PAPER_KIT):
    require(seats in (3, 4, 5), "use three to five seats with this tile supply")
    require(len(kit) == len(PAPER_KIT), "use a sixteen-tile kit")
    tiles = list(kit)
    rng.shuffle(tiles)
    roles = ["good"] * (seats - 1) + ["bad"]
    rng.shuffle(roles)
    return {
        "goal": [4, 2],
        "roles": roles,
        "hands": [tiles[i : i + 2] for i in range(0, 2 * seats, 2)],
        "store": tiles[2 * seats :],
    }


class DecisionConflict(ValueError):
    """The client's decision window has closed or is not open to that seat."""


class Table:
    def __init__(
        self, setup, rng, seconds=60, discussion=15, *, color_teams=False, placement_check=None
    ):
        require(isfinite(seconds) and seconds > 0, "decision time must be positive")
        require(isfinite(discussion) and discussion >= 0, "discussion time must be nonnegative")
        require(placement_check in (None, "edge", "edge-and-marker"), "unknown placement check")
        self.placement_check = placement_check
        self.game = Game(setup)
        self.pieces = [{} for _ in self.game.hands]
        self.next_handle = [1 for _ in self.game.hands]
        for seat, hand in enumerate(self.game.hands):
            self.add_pieces(seat, hand)
        self.rng = rng
        self.seconds = seconds
        self.discussion = discussion
        self.record = new_record(setup)
        if placement_check:
            self.record["placement_check"] = placement_check
        if color_teams:
            self.record["team_names"] = "colors"
        self.history = [[] for _ in self.game.roles]
        self.floor_turns = []
        self.placed_at = None
        self.ready = set()
        self.started = False
        self.votes = {}
        self.speakers = set()
        self.opens = self.deadline = 0

    @property
    def revision(self):
        return len(self.record["events"])

    def join(self, seat, now):
        self.ready.add(seat)
        if not self.started and len(self.ready) == len(self.game.roles):
            self.started = True
            self.open_decision(now)

    def add_pieces(self, seat, faces):
        for face in faces:
            handle = f"H{self.next_handle[seat]}"
            self.next_handle[seat] += 1
            self.pieces[seat][handle] = (face, 0)

    def orient(self, seat, revision, handle, rotation, now):
        self.tick(now)
        if (
            type(revision) is not int
            or revision != self.revision
            or self.game.winner
            or seat not in self.game.alive
            or seat not in self.ready
        ):
            raise DecisionConflict("Hand is closed at this revision")
        require(isinstance(handle, str) and handle in self.pieces[seat], "unknown held piece")
        require(type(rotation) is int and 0 <= rotation < 4, "choose 0–3 clockwise quarter turns")
        face, _ = self.pieces[seat][handle]
        self.pieces[seat][handle] = (face, rotation)

    def commit(self, event, *, handle=None):
        game = self.game
        before = copy(game)
        before.alive = game.alive.copy()
        before.queue = game.queue.copy()
        game.apply(event)
        self.record["events"].append(event)
        kind = event["kind"]
        if kind == "draw":
            self.add_pieces(before.actor, event["tiles"])
        elif kind in ("place", "discard"):
            pieces = self.pieces[before.actor]
            if handle is None:
                handle = next(h for h, (face, _) in pieces.items() if face == event["tile"])
            del pieces[handle]
        if kind == "place":
            self.placed_at = tuple(event["at"])
        if kind == "move_vote" or (kind == "propose" and event["to"] is None):
            if kind == "move_vote":
                result = "stepped" if game.marker != before.marker else "step_rejected"
            else:
                result = "proposal_timed_out" if event.get("timeout") else "builder_stayed"
            self.floor_turns.append(
                {
                    "turn": before.turn,
                    "builder": before.actor,
                    "tile_at": self.placed_at,
                    "marker_before": before.marker,
                    "step_requested": before.pending if kind == "move_vote" else None,
                    "marker_after": game.marker,
                    "result": result,
                }
            )
        for seat, log in enumerate(self.history):
            message = describe(before, event, seat)
            if event["kind"] == "eliminate_vote":
                message += (
                    f" P{before.pending} was eliminated."
                    if before.pending not in game.alive
                    else " Nomination failed."
                )
            if event["kind"] == "move_vote":
                message += f" Marker at {game.marker}."
            log.append({"turn": before.turn, "event": self.revision, "text": message})

    def open_decision(self, now):
        game = self.game
        if game.stage == "draw":
            self.commit(
                {"kind": "draw", "tiles": self.rng.sample(game.store, min(2, len(game.store)))}
            )
        self.votes.clear()
        self.speakers.clear()
        self.opens = now + (self.discussion if game.stage in BALLOTS else 0)
        self.deadline = self.opens + self.seconds

    def reveal(self):
        self.commit(
            {"kind": self.game.stage, "votes": [self.votes.get(s) for s in self.game.alive]}
        )

    def tick(self, now):
        if self.started and not self.game.winner and now >= self.deadline:
            if self.game.stage in BALLOTS:
                self.reveal()
            else:
                self.commit(timeout(self.game, self.rng))
            self.open_decision(now)

    def choices(self, seat, now):
        game = self.game
        if not self.started or game.winner or seat not in game.alive or now < self.opens:
            return None
        if game.stage in BALLOTS:
            return None if seat in self.votes else {"vote": [True, False]}
        if game.stage == "nominate":
            return (
                {"target": [None, *[s for s in game.alive if s != seat]]}
                if seat == game.queue[0]
                else None
            )
        if seat != game.actor:
            return None
        if game.stage == "propose":
            return {"to": [None, *moves(game.board, game.marker)]}
        fields = {"tile": sorted(set(game.hands[seat]))}
        if game.stage == "place":
            fields.update(at=frontier(game.board, game.goal), rotation=list(range(4)))
            if self.placement_check:
                fields.update(
                    origin=sorted(game.board.keys() - {game.goal}), can_step=[True, False]
                )
                if self.placement_check == "edge-and-marker":
                    fields["marker_on_origin"] = [True, False]
        return fields

    def speaking(self, seat, now):
        return (
            self.started
            and not self.game.winner
            and self.game.stage in BALLOTS
            and now < self.opens
            and seat in self.game.alive
            and seat not in self.speakers
        )

    def view(self, seat, now):
        self.tick(now)
        game = self.game
        phase = (
            "lobby"
            if not self.started
            else "over"
            if game.winner
            else ("discussion" if now < self.opens else "decision")
        )
        end = self.opens if phase == "discussion" else self.deadline
        return {
            **({"team_names": "colors"} if self.record.get("team_names") == "colors" else {}),
            "seat": seat,
            "phase": phase,
            "revision": self.revision,
            "seconds_left": max(0, end - now) if phase in ("discussion", "decision") else None,
            "ready_count": len(self.ready),
            "ready": seat in self.ready,
            "voted": seat in self.votes,
            "can_speak": self.speaking(seat, now),
            "state": game.view(seat),
            "pieces": self.pieces[seat].copy(),
            "choices": self.choices(seat, now),
            "history": list(self.history[seat]),
            "floor_turns": [row.copy() for row in self.floor_turns],
        }

    def submit(self, seat, revision, choice, now):
        self.tick(now)
        fields = self.choices(seat, now)
        if type(revision) is not int or revision != self.revision or fields is None:
            raise DecisionConflict("Decision is closed for this seat")
        handle = None
        if (
            isinstance(choice, dict)
            and "piece" in choice
            and self.game.stage in ("place", "discard")
        ):
            choice = choice.copy()
            handle = choice.pop("piece")
            require(isinstance(handle, str) and handle in self.pieces[seat], "unknown held piece")
            require("tile" not in choice, "choose one held piece")
            face, orientation = self.pieces[seat][handle]
            choice["tile"] = face
            if self.game.stage == "place":
                if "expected_orientation" in choice:
                    expected = choice.pop("expected_orientation")
                    require(
                        type(expected) is int and "rotation" not in choice,
                        "choose an expected hand orientation or a direct rotation",
                    )
                    if expected != orientation:
                        raise DecisionConflict("held orientation changed; refresh the hand")
                choice.setdefault("rotation", orientation)
        require(
            isinstance(choice, dict) and choice.keys() == fields.keys(), "invalid choice fields"
        )
        if self.game.stage in BALLOTS:
            require(type(choice["vote"]) is bool, "expected a yes/no vote")
            self.votes[seat] = choice["vote"]
            if len(self.votes) < len(self.game.alive):
                return
            self.reveal()
        else:
            if self.game.stage == "place" and self.placement_check:
                g = self.game
                placement = checked_placement(g.board, g.goal, g.marker, g.hands[seat], choice)
                self.commit({"kind": "place", **placement}, handle=handle)
                dest = tuple(placement["at"])
                step = "open" if choice["can_step"] else "blocked"
                possible = "legal" if dest in moves(g.board, g.marker) else "unavailable"
                self.history[seat][-1]["text"] += (
                    f" You checked {tuple(choice['origin'])} to {dest}: {step}. "
                    f"Marker still at {g.marker}. A direct step from there to {dest} is {possible}."
                )
            else:
                self.commit({"kind": self.game.stage, **choice}, handle=handle)
        self.open_decision(now)

    def say(self, seat, revision, message, now):
        self.tick(now)
        if type(revision) is not int or revision != self.revision or not self.speaking(seat, now):
            raise DecisionConflict("Discussion is closed for this seat")
        require(
            isinstance(message, str) and 0 < len(message.strip()) <= 500, "use 1–500 characters"
        )
        self.speakers.add(seat)
        note = {"after_event": revision, "seat": seat, "text": message.strip()}
        self.record.setdefault("remarks", []).append(note)
        for log in self.history:
            log.append(
                {"turn": self.game.turn, "event": revision, "text": f"P{seat}: {note['text']}"}
            )
