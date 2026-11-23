import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from experiments import persistent_runtime as runtime
from experiments import persistent_table
from footsteps.ollama import ServiceError
from footsteps.record import read, replay
from footsteps.session import Session
from footsteps.table import Table


def reply(name, **arguments):
    return {"message": {"tool_calls": [{"function": {"name": name, "arguments": arguments}}]}}


class PersistentRuntime(unittest.TestCase):
    def test_one_seat_records_private_errors_and_only_validated_lookup_filters(self):
        secret = "private hand and plan"
        calls = iter(
            [
                reply("compact", summary=secret),
                reply("history", kind=secret),
                reply(secret),  # Unknown tool names are also free-form model text.
                reply("history", kind="draw", turn=1),
                reply("place_tile", piece="H1", x=0, y=1),
                reply("stay"),
            ]
        )

        class ScriptedSession(Session):
            def step(self, model, **kwargs):
                return super().step(model, infer=lambda *_: next(calls), **kwargs)

        table = Table(
            {"roles": ["blue"], "goal": [2, 0], "hands": [[255]], "store": [0]}, Random(1)
        )
        with TemporaryDirectory() as tmp, patch.object(runtime, "request") as warmup:
            root, trace = Path(tmp) / "run", Path(tmp) / "owner.jsonl"
            with redirect_stdout(io.StringIO()):
                runtime.play_table(
                    root,
                    trace,
                    "mock",
                    table,
                    0,
                    context=4096,
                    session_class=ScriptedSession,
                    compact_when=lambda _: True,
                )
            self.assertEqual(warmup.call_args.args[2]["options"]["num_ctx"], 4096)
            self.assertEqual(replay(read(root / "game.json")).winner, "red")
            self.assertEqual(trace.stat().st_mode & 0o077, 0)
            self.assertIn(secret, trace.read_text())
            metrics = (root / "calls.jsonl").read_text()
            self.assertNotIn(secret, metrics)
            rows = list(map(json.loads, metrics.splitlines()))
            self.assertTrue(rows[0]["forced_compaction"])
            opening = rows[0]["opportunity"]
            self.assertEqual(
                set(opening),
                {"turn", "stage", "phase", "can_speak", "owe_action", "seconds_left_in_phase"},
            )
            self.assertEqual((opening["stage"], opening["owe_action"]), ("place", True))
            self.assertEqual(rows[1]["filters"], {})
            self.assertTrue(rows[1]["error"])
            self.assertEqual(rows[2]["tool"], "unavailable_tool")
            self.assertEqual(rows[3]["filters"], {"kind": "draw", "turn": 1})
            self.assertEqual(rows[3]["entry_ids"], [1])
            self.assertFalse(rows[3]["forced_compaction"])

    def test_transient_measurement_and_permanent_failure(self):
        session = Mock(snap={"revision": 17})
        with patch.object(runtime, "sleep"):
            for error in (TimeoutError(), ServiceError(500)):
                session.step.side_effect = error
                row = runtime.measured_step(session, "mock")
                public = runtime.public_call(row, "mock", False)
                self.assertEqual(public["revision"], 17)
                self.assertTrue(public["request_error"])
                self.assertIsNone(public["reply_tokens"])
            session.step.side_effect = ServiceError(401)
            with self.assertRaises(ServiceError):
                runtime.measured_step(session, "mock")

    def test_queued_seats_commit_and_report_a_replayable_game(self):
        def infer(_port, _path, body, _timeout):
            state = json.loads(body["messages"][-1]["content"])
            if not state["owe_action"]:
                return reply("wait")
            turn = state["turn"]
            return {
                "place": reply("place_tile", piece="H1", x=-1, y=turn - 1),
                "discard": reply("return_tile", piece="H2"),
                "propose": reply("propose_step", x=turn - 2, y=0),
                "move_vote": reply("vote_move", approve=True),
                "nominate": reply("pass_nomination"),
            }[state["stage"]]

        resident = {"name": "mock", "size": 100, "size_vram": 100, "context_length": 4096}
        with (
            TemporaryDirectory() as tmp,
            patch.object(runtime, "request", side_effect=[{}, {"models": [resident]}]),
            patch.object(persistent_table, "request", side_effect=infer),
        ):
            root = Path(tmp) / "game"
            persistent_table.play(root, Path(tmp) / "private", "mock", 4096, 10, 0)
            record = read(root / "game.json")
            self.assertEqual(replay(record).winner, "blue")
            self.assertEqual(record["events"][-1]["votes"], [True, True, True])
            timing = json.loads((root / "timing.json").read_text())
            self.assertEqual(timing["resident"]["context_length"], 4096)
            report = io.StringIO()
            with redirect_stdout(report):
                persistent_table.report(root)
            self.assertIn(
                "timely discussion windows 0 / 0 remarks 0 timely decisions 15 / 15",
                report.getvalue(),
            )

    def test_archived_report_counts_only_living_voters_and_ready_replies(self):
        root = Path(__file__).resolve().parents[1] / "experiments/persistent-panel/three-9b-30s"
        with redirect_stdout(output := io.StringIO()):
            persistent_table.report(root)
        self.assertIn(
            "timely discussion windows 11 / 11 remarks 11 timely decisions 22 / 24",
            output.getvalue(),
        )
