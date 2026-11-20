import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from footsteps.decision_notes import open_private, read_notes, save_private_export
from footsteps.ollama import infer, model_request
from footsteps.record import read
from footsteps.seat_tools import query
from footsteps.viewer import export_html, transcript

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/crossing.json"


class SeatTools(unittest.TestCase):
    def setUp(self):
        self.record = read(EXAMPLE)
        self.record["table_id"] = "demo-private-id"
        self.snap = {
            "table_id": self.record["table_id"],
            "revision": 4,
            "seat": 2,
            "choices": {"vote": [True, False]},
            "history": [],
            "state": {
                "stage": "move_vote",
                "turn": 1,
                "marker": [0, 0],
                "goal": [2, 0],
                "pending": [1, 0],
                "board": [[[0, 0], 255], [[1, 0], 40], [[2, 0], 255]],
                "store_count": 1,
                "role": "blue",
                "hand": [33],
            },
        }
        self.note = {
            "version": 1,
            "table_id": self.record["table_id"],
            "model": "demo",
            "seat": 2,
            "stage": "move_vote",
            "revision": 4,
            "turn": 1,
            "choice": {"vote": True},
            "reason": "PRIVATE </script> note",
        }
        self.note_json = io.StringIO()

    def test_rotation_answers_use_the_private_hand_and_clockwise_convention(self):
        snap = {
            **self.snap,
            "state": {**self.snap["state"], "stage": "place", "hand": [33, 33]},
            "choices": {"tile": [33], "at": [[0, 1]], "rotation": [3, 2, 1, 0]},
        }
        table = query(snap, "inspect_rotations", {"tile": 33})
        self.assertEqual(
            table["rows_quarter_turns_entrances_exits"],
            [[0, "N", "E"], [1, "E", "S"], [2, "S", "W"], [3, "W", "N"]],
        )
        body = model_request(snap, "demo", show_rotations=True, named_rotations=True)
        context = json.loads(body["messages"][1]["content"])
        self.assertEqual(context["hand_rotations"], [table])
        self.assertEqual(context["options"]["rotation"], ["turn_3", "turn_2", "turn_1", "turn_0"])
        self.assertEqual(snap["choices"]["rotation"], [3, 2, 1, 0])
        with self.assertRaises(ValueError):
            query(snap, "inspect_rotations", {"tile": 8})
        with self.assertRaises(ValueError):
            query(self.snap, "inspect_rotations", {"tile": 33})

    @patch("footsteps.ollama.request")
    def test_rotation_offer_distinguishes_skip_from_cutoff_and_applies_named_turn(self, call):
        snap = {
            **self.snap,
            "state": {**self.snap["state"], "stage": "place"},
            "choices": {"tile": [33], "at": [[0, 1]], "rotation": [3, 2, 1, 0]},
        }
        for reply, status in [
            ({"message": {"content": "{}"}, "done_reason": "stop"}, "skipped"),
            ({"message": {"content": "unfinished"}, "done_reason": "length"}, "truncated"),
            (
                {
                    "message": {
                        "tool_calls": [
                            {"function": {"name": "inspect_rotations", "arguments": {"tile": 33}}}
                        ]
                    }
                },
                "answered",
            ),
        ]:
            notes = io.StringIO()
            call.side_effect = [
                reply,
                {
                    "message": {
                        "content": '{"at":0,"tile":0,"rotation":"turn_1","reason":"turn clockwise"}'
                    }
                },
            ]
            choice = infer(
                snap, "demo", 10, rotation_aid="tool", named_rotations=True, note_file=notes
            )
            self.assertEqual(choice, {"tile": 33, "rotation": 1, "at": [0, 1]})
            (receipt,) = json.loads(notes.getvalue())["tools"]
            self.assertEqual(receipt["status"], status)
            if status == "answered":
                self.assertEqual(receipt["tile"], 33)
                self.assertEqual(
                    call.call_args.args[2]["messages"][-1]["tool_name"], "inspect_rotations"
                )

    def test_checked_geometry_and_illegal_tool_input(self):
        report = query(self.snap, "compare_landings", {})
        self.assertEqual([o["optimistic_steps"] for o in report["landings"]], [None, 1])
        self.assertNotIn("hand", json.dumps(report))
        snap = {
            **self.snap,
            "choices": {"tile": [8], "rotation": [0, 1, 2, 3], "at": [[0, 1]]},
            "state": {**self.snap["state"], "stage": "place"},
        }
        result = query(snap, "preview_placement", {"tile": 8, "rotation": 0, "x": 0, "y": 1})
        self.assertEqual(result["oriented_face"], 8)
        for args in (
            {"tile": True, "rotation": 0, "x": 0, "y": 1},
            {"tile": 33, "rotation": 0, "x": 0, "y": 1},
        ):
            with self.assertRaises(ValueError):
                query(snap, "preview_placement", args)
        with self.assertRaises(ValueError):
            query(snap, "read_store", {})

    @patch("footsteps.ollama.request")
    def test_native_tool_then_action_discards_private_text(self, call):
        call.side_effect = [
            {
                "message": {
                    "tool_calls": [{"function": {"name": "compare_landings", "arguments": {}}}]
                }
            },
            {
                "message": {
                    "content": '{"vote":"approve","reason":"PRIVATE one more step."}',
                    "thinking": "never save",
                }
            },
        ]
        result = infer(
            self.snap, "test", 10, use_tools=True, named_ballots=True, note_file=self.note_json
        )
        self.assertEqual(result, {"vote": True})
        first, second = [c.args for c in call.call_args_list]
        self.assertIn("tools", first[2])
        self.assertLessEqual(first[3], 5)
        self.assertLessEqual(second[3], 10)
        self.assertNotIn("tools", second[2])
        self.assertEqual(second[2]["messages"][-1]["tool_name"], "compare_landings")
        note = json.loads(self.note_json.getvalue())
        self.assertEqual(note["reason"], "PRIVATE one more step.")
        self.assertEqual(note["tools"], [{"name": "compare_landings", "ok": True}])
        self.assertNotIn("never save", self.note_json.getvalue())

    @patch("footsteps.ollama.request")
    def test_optional_tool_or_note_may_be_absent(self, call):
        call.side_effect = [TimeoutError("tool selection"), {"message": {"content": '{"vote":1}'}}]
        self.assertEqual(
            infer(self.snap, "test", 10, use_tools=True, note_file=self.note_json), {"vote": False}
        )
        self.assertIsNone(json.loads(self.note_json.getvalue())["reason"])
        call.reset_mock()
        call.side_effect = None
        call.return_value = {"message": {"content": '{"vote":0}'}}
        self.assertEqual(infer(self.snap, "test", 10), {"vote": True})
        self.assertEqual(call.call_count, 1)
        self.assertNotIn("reason", call.call_args.args[2]["format"]["properties"])

    def test_omniscient_attachment_matched_vote_and_timeout(self):
        self.note["tools"] = [{"name": "compare_landings", "ok": True, "internal": "private debug"}]
        notes = [self.note, {**self.note, "seat": 0}]
        fs = transcript(self.record, omniscient=True, notes=notes)["frames"]
        self.assertEqual([n["matches"] for n in fs[5]["decision_notes"]], [False, True])
        self.assertEqual(
            fs[5]["decision_notes"][0]["tools"], [{"name": "compare_landings", "ok": True}]
        )
        self.assertTrue(all("decision_notes" not in f for i, f in enumerate(fs) if i != 5))
        for seat in (None, 0):
            with self.assertRaisesRegex(ValueError, "omniscient"):
                export_html(self.record, "demo", seat, notes=notes)
            self.assertNotIn("PRIVATE", export_html(self.record, "demo", seat))
        page = export_html(self.record, "demo", omniscient=True, notes=notes)
        self.assertNotIn(self.note["reason"], page)
        self.assertIn("PRIVATE \\u003c/script>", page)
        for red in (
            {"table_id": "another"},
            {"revision": 100},
            {"stage": "place"},
            {"seat": True},
            {"turn": 3},
        ):
            with self.assertRaises(ValueError):
                transcript(self.record, omniscient=True, notes=[{**self.note, **red}])

    def test_file_permissions_and_fresh_note_names(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "seat.jsonl"
            with open_private(p) as handle:
                handle.write(json.dumps(self.note) + "\n")
            self.assertEqual(p.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                open_private(p)
            self.assertEqual(read_notes([p]), [self.note])
            html = Path(folder) / "view.html"
            html.write_text("old")
            html.chmod(0o644)
            save_private_export(html, "private")
            self.assertEqual(html.stat().st_mode & 0o777, 0o600)
            self.assertEqual(html.read_text(), "private")
