import io
import json
import unittest
from random import Random

from footsteps.action_tools import native_decision
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

    def test_native_retry_then_checked_commit_uses_same_oriented_copy(self):
        t = self.table()
        t.placement_check = "edge-and-marker"
        snap = t.view(0, 0)
        calls = iter(
            [
                ("orient_tile", {"piece": "H2", "rotation": True}),
                ("orient_tile", {"piece": "H2", "rotation": 1}),
                ("preview_placement", {"piece": "H2", "x": -1, "y": 0}),
                (
                    "place_tile",
                    {
                        "piece": "H2",
                        "x": -1,
                        "y": 0,
                        "origin_x": 0,
                        "origin_y": 0,
                        "can_step": False,
                        "marker_on_origin": True,
                    },
                ),
                (
                    "place_tile",
                    {
                        "piece": "H2",
                        "x": -1,
                        "y": 0,
                        "origin_x": 0,
                        "origin_y": 0,
                        "can_step": True,
                        "marker_on_origin": True,
                        "reason": "West from START.",
                    },
                ),
            ]
        )

        def ask(port, path, body, left):
            self.assertNotIn("format", body)
            self.assertGreater(left, 0)
            name, args = next(calls)
            return {"message": {"tool_calls": [{"function": {"name": name, "arguments": args}}]}}

        log = []
        notes = io.StringIO()
        choice = native_decision(
            snap,
            "stub",
            5,
            mode="hand",
            trace=log,
            note_file=notes,
            orient=lambda h, r: t.orient(0, 1, h, r, 0),
            request_fn=ask,
        )
        t.submit(0, 1, choice, 0)
        self.assertEqual([r["status"] for r in log], ["rejected", "ok", "ok", "rejected", "commit"])
        self.assertTrue(log[2]["result"]["can_step_here"])
        self.assertEqual(
            t.record["events"][-1], {"kind": "place", "tile": 33, "at": [-1, 0], "rotation": 1}
        )
        self.assertEqual(
            json.loads(notes.getvalue())["choice"], {"tile": 33, "at": [-1, 0], "rotation": 1}
        )

    def test_unplaced_piece_survives_and_returned_face_gets_a_fresh_handle(self):
        t = Table(
            {"roles": ["good"], "hands": [[33, 33]], "store": [33, 33, 33], "goal": [4, 2]},
            Random(4),
        )
        t.join(0, 0)
        t.orient(0, 1, "H2", 3, 0)
        t.submit(0, 1, {"piece": "H3", "at": [1, 0]}, 0)
        t.submit(0, 2, {"piece": "H1"}, 0)
        t.submit(0, 3, {"to": None}, 0)
        pieces = t.view(0, 0)["pieces"]
        self.assertEqual(pieces, {"H2": (33, 3), "H4": (33, 0), "H5": (33, 0), "H6": (33, 0)})
