import json
import unittest
from pathlib import Path
from random import Random
from unittest.mock import Mock, patch

from footsteps.ollama import Seat, ServiceError, infer, model_request, play_seat
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

    def test_guided_placement_supplies_legal_forward_triples(self):
        body = model_request(self.build, "test", guided=True)
        context = json.loads(body["messages"][1]["content"])
        options = context["options"]
        self.assertEqual(len(context["forward_examples"]), 1)
        (hint,) = context["forward_examples"]
        placement = {k: values[hint[k]] for k, values in options.items()}
        game = Table(read(CROSSING)["setup"], Random(1), discussion=0)
        for seat in range(4):
            game.join(seat, 0)
        game.submit(0, 1, placement, 0)
        game.submit(0, 2, {"tile": game.game.hands[0][0]}, 0)
        self.assertIn(tuple(placement["at"]), game.choices(0, 0)["to"])
        self.assertEqual(tuple(placement["at"]), (1, 0))
        plain = model_request(self.build, "test")
        self.assertNotIn("forward_examples", plain["messages"][1]["content"])

    @patch("footsteps.ollama.request")
    def test_named_moves_keep_legal_destinations_under_reordering(self, request):
        snap = {
            **self.ballot,
            "state": {**self.ballot["state"], "stage": "propose"},
            "choices": {"to": [[1, 0], None]},
        }
        for name, dest in (("east", [1, 0]), ("stay", None)):
            request.return_value = {"message": {"content": json.dumps({"to": name})}}
            self.assertEqual(infer(snap, "test", 1, named_moves=True, no_think=True), {"to": dest})
            body = request.call_args.args[2]
            self.assertIs(body["think"], False)
            self.assertEqual(body["format"]["properties"]["to"]["enum"], ["east", "stay"])
        request.return_value = {"message": {"content": '{"to":"west"}'}}
        with self.assertRaises(ValueError):
            infer(snap, "test", 1, named_moves=True)
        self.assertEqual(
            model_request(self.ballot, "test", named_moves=True), model_request(self.ballot, "test")
        )

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

    def test_seat_link_and_model_budget_validation(self):
        for url in ["127.0.0.1", "http://127.0.0.1:8000/", "http://127.0.0.1:8000/state#token"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                Seat(url)
        for budget in [0, -1, float("nan"), float("inf")]:
            seat = Mock()
            with self.subTest(budget=budget), self.assertRaises(ValueError):
                play_seat(seat, "fixture", budget)
            seat.call.assert_not_called()

    @patch("footsteps.ollama.time.sleep")
    def test_closed_window_refreshes_without_resubmitting(self, _sleep):
        over = {"phase": "over", "state": {"winner": "bad"}}
        seat = Mock()
        seat.call.side_effect = [self.ballot, ServiceError(409), over]
        decide = Mock(return_value={"vote": True})
        self.assertEqual(play_seat(seat, "test", 10, decide=decide, report=Mock()), "bad")
        self.assertEqual(
            [c.args[0] for c in seat.call.call_args_list], ["/ready", "/choice", "/state"]
        )
        decide.assert_called_once()
        seat.call.side_effect = [self.ballot, ServiceError(401)]
        with self.assertRaises(ServiceError) as error:
            play_seat(seat, "test", 10, decide=decide, report=Mock())
        self.assertEqual(error.exception.status, 401)

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
