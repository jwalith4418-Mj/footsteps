import json
import unittest
from pathlib import Path
from random import Random
from unittest.mock import Mock, patch

from footsteps.ollama import infer, model_request, play_seat
from footsteps.record import read
from footsteps.table import Table

CROSSING = Path(__file__).resolve().parents[1] / "examples/crossing.json"


class ModelSeat(unittest.TestCase):
    def setUp(self):
        record = read(CROSSING)
        table = Table(record["setup"], Random(1), discussion=0)
        for seat in range(4):
            table.join(seat, 0)
        self.build = table.view(0, 1)
        for event in record["events"][1:4]:
            table.submit(0, table.revision, {k: v for k, v in event.items() if k != "kind"}, 1)
        self.ballot = table.view(2, 1)

    def test_model_context_uses_only_the_seat(self):
        payload = model_request(self.ballot, "test")
        context = json.loads(payload["messages"][1]["content"])
        self.assertEqual(context["hand"], [[33, "N", "E"]])
        self.assertEqual(context["options"], {"vote": [True, False]})
        self.assertTrue({"hands", "roles", "store", "token", "teammates"}.isdisjoint(context))
        self.assertEqual(context["recent"][0], "P0 drew 2 tiles.")
        self.assertEqual(context["recent"][2], "P0 returned a tile to the store.")
        self.assertEqual(context["pending"], [1, 0])
        self.assertEqual(payload["format"]["properties"]["vote"]["enum"], [0, 1])

    @patch("footsteps.ollama.request")
    def test_boolean_vote_and_multi_field_indices(self, request):
        request.return_value = {"message": {"content": '{"vote":1}'}}
        self.assertEqual(infer(self.ballot, "test", 1), {"vote": False})
        request.return_value = {"message": {"content": '{"tile":2,"rotation":3,"at":0}'}}
        expected = {"tile": 40, "rotation": 3, "at": self.build["choices"]["at"][0]}
        self.assertEqual(infer(self.build, "test", 1), expected)
        for bad in ('{"vote":true}', '{"vote":-1}', '{"vote":2}', "{}", "null", "text"):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                request.return_value = {"message": {"content": bad}}
                infer(self.ballot, "test", 1)

    @patch("footsteps.ollama.time.sleep")
    @patch("footsteps.ollama.time.monotonic", side_effect=[0, 2, 3, 3.1])
    def test_late_reply_is_dropped_once_then_next_decision_runs(self, clock, sleep):
        over = {"phase": "over", "state": {"winner": "good"}}
        seat = Mock()
        seat.call.side_effect = [self.ballot, self.ballot, {**self.ballot, "revision": 6}, over]
        model = Mock(return_value={"vote": True})
        play_seat(seat, "test", 1, decide=model, report=Mock())
        self.assertEqual(model.call_count, 2)
        seat.call.assert_called_with("/choice", {"revision": 6, "choice": {"vote": True}})
        self.assertEqual(
            [c.args[0] for c in seat.call.call_args_list], ["/ready", "/state", "/state", "/choice"]
        )
