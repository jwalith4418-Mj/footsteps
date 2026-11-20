import unittest
from random import Random

from footsteps.record import replay
from footsteps.table import DecisionConflict, Table


class PrivateHand(unittest.TestCase):
    def table(self):
        t = Table(
            {
                "roles": ["good", "bad"],
                "hands": [[33, 33], [40, 40]],
                "store": [33, 33, 33],
                "goal": [4, 2],
            },
            Random(2),
        )
        for s in (0, 1):
            t.join(s, 0)
        return t

    def test_orient_duplicate_commit_and_redraw(self):
        t = self.table()
        bystander = t.view(1, 0)
        t.orient(0, 1, "H2", 3, 0)
        t.orient(0, 1, "H2", 3, 0)
        self.assertEqual(t.view(1, 0), bystander)
        self.assertEqual(t.view(0, 0)["pieces"]["H2"], (33, 3))
        with self.assertRaisesRegex(ValueError, "changed"):
            t.submit(0, 1, {"piece": "H2", "at": [1, 0], "expected_orientation": 1}, 0)
        t.submit(0, 1, {"piece": "H1", "at": [1, 0]}, 0)
        self.assertEqual(t.record["events"][-1]["rotation"], 0)
        self.assertEqual(t.pieces[0]["H2"], (33, 3))
        t.submit(0, 2, {"piece": "H2"}, 0)
        self.assertNotIn("H2", t.pieces[0])
        t.submit(0, 3, {"to": None}, 0)
        while t.game.stage == "nominate":
            t.submit(t.game.queue[0], t.revision, {"target": None}, 0)
        self.assertTrue(all(turns == 0 for _, turns in t.pieces[1].values()))
        self.assertEqual(replay(t.record).board, t.game.board)
        self.assertNotIn("H2", str(t.record))

    def test_private_orientation_preserves_timeout(self):
        t, control = self.table(), self.table()
        t.orient(0, 1, "H1", 2, 0)
        with self.assertRaises(DecisionConflict):
            t.orient(0, 1, "H1", 0, t.deadline)
        control.tick(control.deadline)
        self.assertEqual(t.record, control.record)
