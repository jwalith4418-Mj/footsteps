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
    PreparedSession,
    digest,
    read_notes,
    write_note,
)


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
            write_note(MODELS["27b"], "deliberate", 3, owner, public)
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
