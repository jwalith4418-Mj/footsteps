import io
import json
import unittest
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from experiments.horizon_votes import fixture, seat_session
from experiments.pregame_analysis import (
    CONTEXT,
    MODELS,
    PROMPTS,
    ROUTE_BOUND,
    PreparedSession,
    digest,
    main,
    read_notes,
    write_note,
)
from footsteps.session import MOVEMENT_CLOCK


class PregameAnalysis(unittest.TestCase):
    def test_private_note_survives_compaction_and_recovery_only_in_its_seat(self):
        prefix = fixture("short", "west")
        note = "private evergreen observation"
        session = seat_session(
            prefix,
            3,
            "blue",
            session_class=partial(PreparedSession, pregame_note=note),
            context=CONTEXT,
        )
        peer = session.seat
        for rolling in ("first observation", "replacement"):
            session.execute(
                "compact", {"summary": rolling}, session.tools(), session.snap["revision"]
            )
            restored = json.loads(session.messages[1]["content"])
            self.assertEqual(restored["your_private_pregame_note"], note)
            self.assertEqual(restored["your_private_player_authored_summary"], rolling)
        self.assertFalse(session.failed_compaction())
        self.assertTrue(session.failed_compaction())
        self.assertEqual(
            json.loads(session.messages[1]["content"])["your_private_pregame_note"], note
        )
        self.assertNotIn(note, session.messages[0]["content"])
        for view in (peer.table.record, peer.call("/session"), peer.table.view(1, 0)):
            self.assertNotIn(note, json.dumps(view))
        control = seat_session(
            prefix, 3, "blue", session_class=partial(PreparedSession, pregame_note="")
        )
        self.assertNotIn("your_private_pregame_note", control.messages[1]["content"])

    def test_unfinished_draft_is_retried_without_publishing_text_or_thinking(self):
        replies = [
            {"done_reason": "length", "message": {"content": "unfinished"}},
            {
                "done_reason": "stop",
                "message": {"content": "private memo", "thinking": "hidden trace"},
                "eval_count": 38,
            },
        ]
        owner, public = io.StringIO(), io.StringIO()
        with patch("experiments.pregame_analysis.request", side_effect=replies) as infer:
            write_note(MODELS["27b"], "deliberate", 1, owner, public)
        a, b = (call.args[2] for call in infer.call_args_list)
        self.assertTrue(a["think"])
        self.assertEqual(a["messages"], b["messages"])
        self.assertGreater(b["options"]["num_predict"], a["options"]["num_predict"])
        self.assertEqual(json.loads(owner.getvalue())["note"], "private memo")
        self.assertNotIn("private memo", public.getvalue())
        self.assertNotIn("hidden trace", owner.getvalue() + public.getvalue())
        self.assertEqual(json.loads(public.getvalue())["sha256"], digest("private memo"))

    def test_transfer_rejects_incomplete_panel_and_modified_note(self):
        note = {
            "cue": "open",
            "seed": 1,
            "model": MODELS["9b"],
            "note": "draft",
            "sha256": digest("draft"),
        }
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "private.jsonl"
            path.write_text(json.dumps(note))
            with self.assertRaisesRegex(ValueError, "incomplete"):
                read_notes(MODELS["9b"], path, {("open", 1), ("invariants", 1)})
            path.write_text(json.dumps(note | {"note": "changed"}))
            with self.assertRaisesRegex(ValueError, "intact"):
                read_notes(MODELS["9b"], path, {("open", 1)})

    def test_clarified_arm_uses_the_normal_live_prompt_after_reset(self):
        prefix = fixture("short", "west")
        live = seat_session(prefix, 3, "red", context=CONTEXT)
        clarified = seat_session(
            prefix,
            3,
            "red",
            session_class=partial(
                PreparedSession, pregame_note="", system_prompt=PROMPTS["clarified-none"]
            ),
            context=CONTEXT,
        )
        original = seat_session(
            prefix,
            3,
            "red",
            session_class=partial(PreparedSession, pregame_note=""),
            context=CONTEXT,
        )
        for session in (live, clarified, original):
            session.reset()
        self.assertEqual(live.messages, clarified.messages)
        self.assertEqual(clarified.messages[1:], original.messages[1:])
        self.assertIn(MOVEMENT_CLOCK, live.messages[0]["content"])
        self.assertNotIn(MOVEMENT_CLOCK, original.messages[0]["content"])

    def test_capped_preparation_keeps_the_failure_and_drops_the_draft(self):
        owner, public = io.StringIO(), io.StringIO()
        with patch(
            "experiments.pregame_analysis.request",
            return_value={"done_reason": "length", "message": {"content": "cut-off draft"}},
        ) as infer:
            write_note(MODELS["27b"], "deliberate", 2, owner, public)
        infer.assert_called_once()
        self.assertIsNone(json.loads(owner.getvalue())["note"])
        self.assertEqual(json.loads(public.getvalue())["status"], "unfinished")
        self.assertNotIn("cut-off draft", owner.getvalue() + public.getvalue())

    def test_taught_condition_survives_a_reset_without_a_private_note(self):
        session = seat_session(
            fixture("detour", "north"),
            3,
            "blue",
            session_class=partial(
                PreparedSession, pregame_note="", system_prompt=PROMPTS["taught-none"]
            ),
            context=CONTEXT,
        )
        session.execute(
            "compact", {"summary": "Ballot open."}, session.tools(), session.snap["revision"]
        )
        self.assertIn(MOVEMENT_CLOCK, session.messages[0]["content"])
        self.assertIn(ROUTE_BOUND, session.messages[0]["content"])
        self.assertNotIn("your_private_pregame_note", json.loads(session.messages[1]["content"]))

    def test_generate_cli_writes_only_a_receipt_to_the_public_log(self):
        with TemporaryDirectory() as tmp:
            owner, receipt = (Path(tmp) / name for name in ("private", "public"))
            with (
                patch(
                    "experiments.pregame_analysis.request",
                    return_value={
                        "done_reason": "stop",
                        "message": {"content": "my private opening memo"},
                    },
                ),
                patch("experiments.pregame_analysis.resident_model", return_value={}),
                patch("sys.stdout", new_callable=io.StringIO),
            ):
                main(["generate", "9b", str(owner), str(receipt), "--clarified"])
            memo, key = (json.loads(p.read_text()) for p in (owner, receipt))
            self.assertEqual(key["sha256"], digest(memo["note"]))
            self.assertEqual(key["cue"], "clarified-invariants")
            self.assertNotIn("note", key)

    def test_extended_preparation_records_realized_usage_and_retains_only_the_note(self):
        owner, receipt = io.StringIO(), io.StringIO()
        reply = {
            "done_reason": "stop",
            "total_duration": 1000000000,
            "eval_count": 7100,
            "prompt_eval_count": 350,
            "message": {"content": "finished", "thinking": "unsaved draft"},
        }
        with patch("experiments.pregame_analysis.request", return_value=reply) as infer:
            write_note(MODELS["27b"], "deliberate-16k", 1, owner, receipt)
        settings = infer.call_args.args[2]["options"]
        self.assertEqual(settings["num_ctx"], 16384)
        self.assertGreater(settings["num_predict"], 6144)
        self.assertEqual(json.loads(owner.getvalue())["note"], "finished")
        record = json.loads(receipt.getvalue())
        self.assertEqual(
            (record["generated_tokens"], record["seconds"], record["done_reason"]),
            (7100, 1, "stop"),
        )
        self.assertNotIn("unsaved draft", owner.getvalue() + receipt.getvalue())

    def test_two_pass_writer_keeps_intermediate_text_out_of_both_artifacts(self):
        owner, receipt = io.StringIO(), io.StringIO()
        replies = [
            {"done_reason": "length", "message": {"thinking": "draft-only text", "content": ""}},
            {"done_reason": "stop", "message": {"content": "my finished strategy"}},
        ]
        with patch("experiments.pregame_analysis.request", side_effect=replies) as infer:
            write_note(MODELS["27b"], "finish-draft", 1, owner, receipt)
        first, second = (call.args[2] for call in infer.call_args_list)
        self.assertTrue(first["think"])
        self.assertFalse(second["think"])
        self.assertIn("draft-only text", second["messages"][-2]["content"])
        self.assertNotIn("draft-only text", owner.getvalue() + receipt.getvalue())
        self.assertEqual(json.loads(owner.getvalue())["note"], "my finished strategy")
        self.assertEqual(json.loads(receipt.getvalue())["attempt_limits"], [3072, 1024])
