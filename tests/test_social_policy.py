import io
import json
import unittest
from copy import deepcopy
from unittest.mock import patch

from experiments.behavior_probe import cases, prefix, tradeoffs
from footsteps.ollama import infer
from footsteps.social import forecast, shortlist, social_request


class SocialPolicy(unittest.TestCase):
    def test_guard_and_ambiguous_choices_are_distinct(self):
        for name, snap, preferred in cases():
            legal = next(iter(snap["choices"].values()))
            with self.subTest(case=name, role=snap["state"]["role"], seat=snap["seat"]):
                if name in ("enter-exit", "seal-marker", "last-blue"):
                    self.assertEqual(shortlist(snap), [preferred])
                    sink = io.StringIO()
                    with patch(
                        "footsteps.ollama.request", side_effect=AssertionError("unneeded inference")
                    ):
                        self.assertEqual(
                            infer(snap, "test", 2, outcome_policy=True, note_file=sink),
                            {"vote": preferred},
                        )
                    self.assertEqual(
                        json.loads(sink.getvalue())["model"], "Footsteps outcome policy"
                    )
                else:
                    self.assertEqual(shortlist(snap), legal)

    def test_conditional_forecast_respects_tie_and_does_not_read_a_ballot(self):
        snap = next(s for name, s, _ in tradeoffs() if name == "free-cover")
        self.assertEqual(forecast(snap), {"yes": "passes", "no": "passes"})
        snap = deepcopy(snap)
        a, b = snap["state"]["alive"][:2]
        snap["state"]["alive"] = [a, b]
        snap["history"] = [{"text": f"P{a}: I intend to vote no.", "event": snap["revision"]}]
        self.assertEqual(forecast(snap), {"yes": "fails", "no": "fails"})
        snap["state"]["actor"] = b
        self.assertEqual(forecast(snap), {"yes": "passes", "no": "fails"})
        snap["state"]["stage"] = "eliminate_vote"
        self.assertEqual(forecast(snap), {"yes": "fails", "no": "fails"})
        snap["revision"] += 1
        self.assertIsNone(forecast(snap))

    def test_partial_menu_decodes_to_the_original_coordinate(self):
        # At start, north/east are viable, west loses on distance. Give the builder
        # enough time to avoid the loss and check the second shortlisted destination.
        snap = next(s for name, s, _ in cases() if name == "ordinary-move")
        snap = deepcopy(snap)
        snap["state"].update(
            stage="propose",
            role="blue",
            goal=(2, 2),
            marker=(0, 0),
            store_count=3,
            board=[((x, y), 255) for x, y in ((0, 0), (0, 1), (1, 0), (-1, 0), (2, 2))],
        )
        snap["choices"] = {"to": [None, (-1, 0), (0, 1), (1, 0)]}
        self.assertEqual(shortlist(snap), [(0, 1), (1, 0)])
        with patch(
            "footsteps.ollama.request",
            return_value={"message": {"content": '{"to":"propose_1_0"}'}},
        ):
            self.assertEqual(infer(snap, "test", 2, outcome_policy=True), {"to": (1, 0)})

    def test_social_note_is_optional_and_pre_vote_history_is_private(self):
        snap = next(s for name, s, _ in cases() if name == "8201-self")
        body = {}
        social_request(body, snap, explain=False)
        self.assertNotIn("reason", body["format"]["properties"])
        self.assertNotIn("votes", snap)
        ctx = json.loads(body["messages"][1]["content"])
        self.assertNotIn("hands", ctx)
        self.assertIn("(you)", ctx["subject"])

    def test_pivotal_risk_has_a_posthumous_winning_continuation(self):
        # With red P2 the next builder after an opening veto is always Blue P1.
        for move in (True, False):
            setup = {
                "roles": ["blue", "blue", "red"],
                "goal": [0, 1],
                "hands": [[8], [8], [8]],
                "store": [32, 32],
            }
            t = prefix(
                setup,
                [
                    {"kind": "draw", "tiles": [32, 32]},
                    {"kind": "place", "tile": 8, "rotation": 0, "at": [1, 0]},
                    {"kind": "discard", "tile": 32},
                    {"kind": "propose", "to": [1, 0]},
                ],
            )
            for s, v in enumerate((True, False, move)):
                t.submit(s, t.revision, {"vote": v}, t.opens)
            if move:
                t.submit(1, t.revision, {"target": 2}, t.opens)
                for s, v in enumerate((True, True, False)):
                    t.submit(s, t.revision, {"vote": v}, t.opens)
            while t.game.stage == "nominate":
                t.submit(t.game.queue[0], t.revision, {"target": None}, t.opens)
            self.assertEqual(t.game.actor, 1)
            t.submit(1, t.revision, {"tile": 8, "rotation": 0, "at": [-1, 0]}, t.opens)
            t.submit(1, t.revision, {"to": None if move else [0, 1]}, t.opens)
            if not move:
                for s, v in enumerate((True, True, False)):
                    t.submit(s, t.revision, {"vote": v}, t.opens)
            self.assertEqual(
                (t.game.winner, 2 in t.game.alive), ("red", False) if move else ("blue", True)
            )
