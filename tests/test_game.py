import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from random import Random

from footsteps.board import connects, moves, rotate
from footsteps.fallback import timeout
from footsteps.game import Game
from footsteps.record import read, render, replay
from footsteps.solo import POLICIES, route_move, sealed, setup, simulate

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = read(ROOT / "examples/crossing.json")


def before(index):
    r = deepcopy(EXAMPLE)
    r["events"] = r["events"][:index]
    return replay(r)


class Rules(unittest.TestCase):
    def test_all_faces_rotate_conjunctively(self):
        for face in range(256):
            for d in range(4):
                for r in range(4):
                    tile = rotate(face, r)
                    self.assertEqual(connects(tile, 255, (d + r) % 4), bool(face & (16 << d)))
                    self.assertEqual(connects(255, tile, (d + r + 2) % 4), bool(face & (1 << d)))
            self.assertEqual(rotate(rotate(face, 1), 3), face)
        self.assertTrue(connects(32, 8, 1))
        self.assertFalse(connects(32, 2, 1))
        self.assertFalse(connects(8, 32, 3))

    def test_frontier_and_immutable_failed_action(self):
        g = before(1)
        original = deepcopy(vars(g))
        for at in ([0, 0], [2, 0], [3, 0], [1, 1]):
            with self.assertRaises(ValueError):
                g.apply({"kind": "place", "at": at, "tile": 40, "rotation": 0})
            self.assertEqual(vars(g), original)
        g.apply({"kind": "place", "at": [-1, 0], "tile": 40, "rotation": 0})
        self.assertNotIn((-1, 0), moves(g.board, g.marker))

    def test_tied_ballots_and_chair_rotation(self):
        for ballot in (False, None):
            g = before(4)
            g.apply({"kind": "move_vote", "votes": [ballot, True, True, False]})
            self.assertEqual(g.marker, (0, 0))
        g = before(6)
        self.assertEqual(g.marker, (1, 0))
        g.apply({"kind": "eliminate_vote", "votes": [True, False, True, None]})
        self.assertEqual(g.alive, [0, 1, 2, 3])
        self.assertEqual(g.queue, [2, 3, 0])

    def test_proposer_can_be_eliminated(self):
        g = before(5)
        g.apply({"kind": "nominate", "target": 0})
        g.apply({"kind": "eliminate_vote", "votes": [True] * 4})
        for who in (2, 3):
            self.assertEqual(g.queue[0], who)
            g.apply({"kind": "nominate", "target": None})
        self.assertEqual((g.actor, g.stage, g.alive), (1, "draw", [1, 2, 3]))

    def test_all_good_gone(self):
        r = deepcopy(EXAMPLE)
        r["setup"]["roles"] = ["bad", "bad", "bad", "good"]
        r["events"] = r["events"][:7]
        self.assertEqual(replay(r).winner, "bad")

    def test_final_draw_and_posthumous_win(self):
        g = before(11)
        self.assertEqual(g.stage, "propose")
        self.assertEqual(g.store, [])
        self.assertEqual(len(g.hands[1]), 1)
        self.assertEqual(g.alive, [0, 1, 2])
        g.apply({"kind": "propose", "to": None})
        self.assertEqual(g.winner, "bad")
        self.assertEqual(replay(EXAMPLE).winner, "good")
        with self.assertRaises(ValueError):
            g.apply({"kind": "draw", "tiles": []})

    def test_privacy(self):
        r = deepcopy(EXAMPLE)
        r["setup"]["roles"] = ["good", "bad", "bad", "good"]
        g = Game(r["setup"])
        self.assertNotIn("hand", g.view())
        self.assertNotIn("teammates", g.view(0))
        self.assertEqual(g.view(1)["teammates"], [2])
        self.assertNotIn("roles", g.view(1))
        g.view(1)["hand"].clear()
        self.assertEqual(g.hands[1], [9])
        self.assertNotIn("roles", before(9).view())
        self.assertEqual(replay(EXAMPLE).view()["roles"], EXAMPLE["setup"]["roles"])
        self.assertNotIn("returned 18", render(EXAMPLE))
        self.assertIn("returned 18", render(EXAMPLE, 0))
        self.assertNotIn("returned 18", render(EXAMPLE, 1))

    def test_timeout_defaults_and_visible_random_choice(self):
        for index in (1, 2, 3, 5):
            g = before(index)
            e = timeout(g, Random(13))
            self.assertTrue(e["timeout"])
            g.apply(e)
        g = before(0)
        with self.assertRaises(ValueError):
            g.apply({"kind": "draw", "tiles": [18, 18]})
        self.assertEqual(g.store, [18, 12])

    def test_versioned_round_trip(self):
        account = render(EXAMPLE, full=True)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "account.md"
            p.write_text(account)
            self.assertEqual(read(p), EXAMPLE)
        self.assertEqual(render(EXAMPLE), (ROOT / "examples/crossing.md").read_text())
        for field in ("format", "rules"):
            r = dict(EXAMPLE, **{field: 999})
            with self.assertRaises(ValueError):
                replay(r)


class Solitaire(unittest.TestCase):
    def test_generated_games_replay_and_conserve_tiles(self):
        for seed in range(8):
            initial = setup(seed, (-3, 2), 0, 8, 0.55)
            for policy in POLICIES:
                a, rec = simulate(initial, seed, policy, True)
                g = replay(json.loads(json.dumps(rec)))
                self.assertEqual(a["win"], int(g.winner == "good"))
                self.assertEqual(len(g.store) + len(g.board) - 2, 8)
                self.assertEqual(g.hands, [[]])
                self.assertEqual((a, rec), simulate(initial, seed, policy, True))

    def test_switch_has_identical_prefix(self):
        for seed in range(20):
            initial = setup(seed, (3, 1), 2, 8, 0.55)
            a, greedy = simulate(initial, seed, "greedy", True)
            b, switch = simulate(initial, seed, "switch", True)
            self.assertEqual(a["near_turn"], b["near_turn"])
            g = Game(initial)
            for left, right in zip(greedy["events"], switch["events"]):
                if g.turn == a["near_turn"]:
                    break
                self.assertEqual(left, right)
                g.apply(left)
            if a["near_turn"] is None:
                self.assertEqual(switch, greedy)

    def test_trap_certificate_and_backtrack(self):
        goal = (2, 0)
        board = {(0, 0): 255, (1, 0): 136, goal: 255}
        self.assertFalse(sealed(board, (1, 0), goal))
        self.assertEqual(route_move(board, (1, 0), goal, Random(1)), (0, 0))
        board[(1, 0)] = 8
        self.assertTrue(sealed(board, (1, 0), goal))
