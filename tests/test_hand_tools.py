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
            self.assertNotIn("zero-based", body["messages"][0]["content"].lower())
            context = json.loads(body["messages"][1]["content"])
            self.assertIn([0, 0], context["origins"])
            self.assertNotIn("origin_indices_by_at_index", context)
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

    def test_confirm_needs_matching_preview_and_can_revise_before_placing(self):
        t = self.table()
        snap = t.view(0, 0)
        responses = iter(
            [
                ("commit_preview", {}),
                ("preview_placement", {"piece": "H1", "x": -1, "y": 0}),
                ("orient_tile", {"piece": "H1", "rotation": 1}),
                ("commit_preview", {}),
                ("preview_placement", {"piece": "H1", "x": -1, "y": 0}),
                ("commit_preview", {}),
            ]
        )

        def ask(port, path, body, seconds):
            name, args = next(responses)
            return {"message": {"tool_calls": [{"function": {"name": name, "arguments": args}}]}}

        log = []
        choice = native_decision(
            snap,
            "stub",
            5,
            mode="draft",
            trace=log,
            prospects=True,
            orient=lambda h, r: t.orient(0, 1, h, r, 0),
            request_fn=ask,
        )
        self.assertEqual(
            [x["status"] for x in log], ["rejected", "ok", "ok", "rejected", "ok", "commit"]
        )
        self.assertFalse(log[1]["result"]["can_step_here"])
        self.assertTrue(log[4]["result"]["can_step_here"])
        self.assertIn("permanent_trap", log[4]["result"])
        self.assertEqual(choice, {"piece": "H1", "at": [-1, 0], "expected_orientation": 1})
        t.submit(0, 1, choice, 0)
        self.assertEqual(t.game.marker, (0, 0))

    def test_rotation_inspection_preserves_piece_and_board(self):
        t = self.table()
        snap = t.view(0, 0)
        log = []
        calls = iter(
            [
                ("inspect_rotations_at", {"piece": "H2", "x": -1, "y": 0}),
                ("place_tile", {"piece": "H2", "x": -1, "y": 0}),
            ]
        )

        def ask(port, path, body, left):
            name, args = next(calls)
            return {"message": {"tool_calls": [{"function": {"name": name, "arguments": args}}]}}

        choice = native_decision(snap, "stub", 5, mode="fit", trace=log, request_fn=ask)
        rows = log[0]["result"]["orientations"]
        self.assertEqual([r["rotation"] for r in rows if r["can_step_here"]], [1])
        self.assertEqual(choice["expected_orientation"], 0)
        self.assertEqual(snap, t.view(0, 0))

    def test_social_tools_reach_referee_with_literal_values(self):
        t = self.table()
        actions = [
            ("place_tile", {"piece": "H2", "x": 0, "y": -1}),
            ("return_tile", {"piece": "H1"}),
            ("propose_step", {"x": 0, "y": -1}),
            ("vote_move", {"approve": True}),
            ("vote_move", {"approve": False}),
            ("nominate", {"seat": 0}),
            ("vote_removal", {"approve": True}),
            ("vote_removal", {"approve": False}),
            ("pass_nomination", {}),
        ]
        for seat, (name, args) in zip((0, 0, 0, 0, 1, 1, 0, 1, 0), actions, strict=True):
            with self.subTest(name=name):

                def ask(port, path, body, left, name=name, args=args):
                    self.assertIn(name, [t["function"]["name"] for t in body["tools"]])
                    return {
                        "message": {"tool_calls": [{"function": {"name": name, "arguments": args}}]}
                    }

                t.submit(
                    seat,
                    t.revision,
                    native_decision(t.view(seat, t.opens), "stub", 5, mode="hand", request_fn=ask),
                    t.opens,
                )
        self.assertEqual(t.game.marker, (0, -1))
        self.assertEqual(t.game.alive, [0, 1])
        self.assertEqual(t.game.turn, 2)
