import io
import json
import unittest
from pathlib import Path
from random import Random
from unittest.mock import patch

from footsteps.board import moves
from footsteps.game import checked_placement
from footsteps.ollama import infer
from footsteps.record import read, replay
from footsteps.table import DecisionConflict, Table
from footsteps.viewer import transcript

RECORD = Path(__file__).resolve().parents[1] / "experiments/exit-origin/social/8602-red1+3.json"


def before_build(mode="edge-and-marker"):
    record = read(RECORD)
    table = Table(record["setup"], Random(80), placement_check=mode)
    table.started = True
    table.deadline = 20
    for event in record["events"][:41]:
        table.commit(event)
    return table


class CheckedPlacement(unittest.TestCase):
    def setUp(self):
        self.choice = {
            "tile": 58,
            "rotation": 0,
            "origin": [-2, -1],
            "at": [-1, -1],
            "can_step": True,
            "marker_on_origin": False,
        }

    def test_private_rejections_then_correct_remote_or_blocking_build(self):
        for rotation, can_step in [(0, True), (1, False)]:
            table = before_build()
            public = table.view(0, 0)
            before = table.view(4, 0)
            valid = {**self.choice, "rotation": rotation, "can_step": can_step}
            for wrong, message in [
                ({"origin": [0, 0]}, "construction neighbor"),
                ({"origin": [3, 3]}, "no floor"),
                ({"origin": [-2, -2]}, "sharing an edge"),
                ({"at": [-2, -1]}, "occupied"),
                ({"tile": 255}, "your hand"),
                ({"rotation": 4}, "rotation"),
                ({"can_step": not can_step}, "entrance"),
                ({"can_step": int(can_step)}, "entrance"),
                ({"marker_on_origin": True}, "marker is at"),
                ({"marker_on_origin": 0}, "marker is at"),
            ]:
                with self.subTest(wrong=wrong), self.assertRaisesRegex(ValueError, message):
                    table.submit(4, 41, valid | wrong, 0)
                self.assertEqual(table.view(0, 0), public)
                self.assertEqual(table.view(4, 0), before)
            table.submit(4, 41, valid, 1)
            self.assertEqual(
                table.record["events"][-1],
                {
                    "kind": "place",
                    "tile": 58,
                    "rotation": rotation,
                    "at": [-1, -1],
                },
            )
            self.assertEqual(table.game.marker, (-2, -2))
            self.assertIn(
                "direct step from there to (-1, -1) is unavailable",
                table.view(4, 1)["history"][-1]["text"],
            )
            self.assertNotIn("You checked", str(table.view(0, 1)))
            self.assertNotIn("You checked", str(transcript(table.record)))
            self.assertEqual(replay(table.record).board, table.game.board)

    def test_timeout_samples_the_original_public_commands(self):
        ordinary, checked = before_build(None), before_build()
        with self.assertRaises(ValueError):
            checked.submit(4, 41, self.choice | {"can_step": False}, 19)
        with self.assertRaises(DecisionConflict):
            checked.submit(4, 41, self.choice, 20)
        ordinary.tick(20)
        self.assertEqual(ordinary.record["events"], checked.record["events"])
        self.assertTrue(checked.record["events"][-1]["timeout"])

    @patch("footsteps.ollama.request")
    def test_model_can_correct_false_marker_claim_without_publishing_it(self, request):
        table = before_build()
        snap = table.view(4, 0)
        opts = snap["choices"]
        build = {k: opts[k].index(v) for k, v in [("at", (-1, -1)), ("tile", 58), ("rotation", 0)]}
        self.assertEqual(opts["marker_on_origin"], [True, False])
        claim = {"origin": "(-2,-1)", "can_step": True, "marker_on_origin": False}
        request.side_effect = [
            {"message": {"content": json.dumps(r)}}
            for r in [
                build | {"reason": "Selected a remote tile."},
                claim | {"marker_on_origin": True},
                claim,
            ]
        ]
        notes = io.StringIO()
        result = infer(snap, "test", 10, note_file=notes)
        table.submit(4, 41, result, 1)
        self.assertEqual(request.call_count, 3)
        self.assertIn("The marker is at", request.call_args.args[2]["messages"][-1]["content"])
        self.assertEqual(
            json.loads(notes.getvalue())["choice"], {"tile": 58, "at": [-1, -1], "rotation": 0}
        )

    def test_marker_can_use_another_neighbor_edge(self):
        table = before_build("edge")
        # The edge from the northern origin is blocked, the edge from the marker is open.
        board = {(-2, 0): 255, (-2, 1): 255, (-1, 1): 0, (0, 0): 255}
        base = {"tile": 8, "rotation": 0, "at": [-1, 0], "origin": [-1, 1], "can_step": False}
        self.assertEqual(checked_placement(board, (0, 0), (-2, 0), [8], base)["at"], [-1, 0])
        self.assertIn((-1, 0), moves({**board, (-1, 0): 8}, (-2, 0)))
        self.assertNotIn("marker_on_origin", table.choices(4, 0))
