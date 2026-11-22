import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from experiments.ballot_thinking import run_vote
from experiments.exit_interest import prefix
from experiments.thinking_view import build
from footsteps.viewer import export_html, transcript


class ThinkingReplay(unittest.TestCase):
    def test_owner_trace_at_unresolved_ballot_is_pending_and_escaped(self):
        r = prefix("trap") | {"table_id": "private"}
        row = {
            "version": 1,
            "kind": "thinking",
            "table_id": "private",
            "revision": 4,
            "turn": 1,
            "stage": "move_vote",
            "seat": 1,
            "model": "m",
            "label": "capped",
            "thinking": "</script>secret",
        }
        for options in ({}, {"seat": 1}):
            with self.assertRaisesRegex(ValueError, "omniscient"):
                transcript(r, notes=[row], **options)
        frames = transcript(r, omniscient=True, notes=[row])["frames"]
        self.assertFalse(any("pending_thinking_traces" in f for f in frames[:-1]))
        self.assertNotIn("thinking_traces", frames[-1])
        self.assertEqual(frames[-1]["pending_thinking_traces"][0]["thinking"], row["thinking"])
        self.assertNotIn(row["thinking"], export_html(r, "test", omniscient=True, notes=[row]))
        with self.assertRaisesRegex(ValueError, "trace does not match"):
            transcript(r, omniscient=True, notes=[row | {"turn": 2}])

    def test_adjacent_nominations_group_attempts_with_the_action_and_keep_open_prefix(self):
        from footsteps.record import read

        path = (
            Path(__file__).resolve().parents[1] / "experiments/seat-payoff/explicit-14101/game.json"
        )
        record = read(path)
        base = {
            "version": 1,
            "kind": "thinking",
            "table_id": record["table_id"],
            "turn": 1,
            "stage": "nominate",
            "model": "test",
            "label": "attempt",
        }
        notes = [
            base | {"seat": who, "revision": rev, "thinking": value}
            for who, rev, value in [(1, 5, "wait"), (1, 5, "pass"), (2, 6, "pass")]
        ]
        full = transcript(record, omniscient=True, notes=notes)["frames"]
        self.assertEqual(full[6]["message"], "P1 passed.")
        self.assertEqual([r["thinking"] for r in full[6]["thinking_traces"]], ["wait", "pass"])
        self.assertEqual(full[7]["message"], "P2 passed.")
        self.assertEqual([r["seat"] for r in full[7]["thinking_traces"]], [2])
        self.assertNotIn("thinking_traces", full[5])
        self.assertFalse(any("pending_thinking_traces" in f for f in full))
        prefix = record | {"events": record["events"][:6], "remarks": []}
        last = transcript(prefix, omniscient=True, notes=notes)["frames"][-1]
        self.assertEqual(last["thinking_traces"], full[6]["thinking_traces"])
        self.assertEqual(last["pending_thinking_traces"], full[7]["thinking_traces"])

    def test_capped_reply_is_kept_only_in_owner_artifact_and_rendered_without_a_vote(self):
        owner = io.StringIO()
        reply = {
            "message": {"thinking": "private text", "content": ""},
            "done_reason": "length",
            "eval_count": 8,
            "prompt_eval_count": 100,
        }
        with patch("experiments.ballot_thinking.request", return_value=reply):
            row = run_vote("test", "trap", "red", 8, owner)
        self.assertIsNone(row["vote"])
        self.assertNotIn("private text", json.dumps(row))
        with TemporaryDirectory() as directory:
            root = Path(directory)
            receipts = root / "receipts"
            receipts.mkdir()
            (receipts / "x.jsonl").write_text(json.dumps(row))
            (root / "x.jsonl").write_text(owner.getvalue())
            build(receipts, root, root / "views")
            view = root / "views/trap-red.html"
            self.assertEqual(view.stat().st_mode & 0o777, 0o600)
            self.assertIn("private text", view.read_text())
            (root / "x.jsonl").write_text(owner.getvalue().replace("private text", "changed"))
            with self.assertRaisesRegex(ValueError, "differs"):
                build(receipts, root, root / "views")

    def test_live_ballot_shares_allowance_across_reads_and_falls_back_after_cap(self):
        from experiments.ballot_thinking import position
        from experiments.thinking_game import BallotSession

        _, base = position("trap", "red")
        peer = base.seat
        original = peer.call

        def call(path, data=None):
            if path == "/ready":
                return {"seat": peer.seat, "table_id": "live-id"}
            return original(path, data)

        peer.call = call
        with TemporaryDirectory() as folder:
            s = BallotSession(
                peer, allowance=8, private=Path(folder), sleep=peer.expire, context=16384
            )
            sent = []

            def infer(port, path, body, timeout):
                sent.append((body["think"], body["options"]["num_predict"]))
                name = "get_state" if len(sent) == 1 else "vote_move"
                return {
                    "eval_count": 4,
                    "done_reason": "length" if len(sent) == 2 else "stop",
                    "message": {
                        "content": "",
                        "thinking": "private" if body["think"] else "",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": name,
                                    "arguments": {} if name == "get_state" else {"approve": True},
                                }
                            }
                        ],
                    },
                }

            for _ in range(3):
                s.step("test", infer=infer)
            self.assertEqual(sent, [(True, 8), (True, 4), (False, 240)])
            rows = [json.loads(l) for l in s.notes.read_text().splitlines()]
            self.assertEqual([r["limit"] for r in rows], [8, 4])
            self.assertTrue(all(r["table_id"] == "live-id" for r in rows))
            self.assertEqual(s.notes.stat().st_mode & 0o777, 0o600)
            self.assertTrue(peer.table.votes[peer.seat])
