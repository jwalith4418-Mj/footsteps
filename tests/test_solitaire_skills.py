import json
import unittest
from unittest.mock import patch

from experiments.model_solitaire import detour_table
from experiments.plan_tactics import position
from experiments.skill_probe import card_choice, optimistic_length, positions
from experiments.turn_plans import plans


class SkillDecisions(unittest.TestCase):
    def test_optimistic_floor_keeps_actual_one_way_edges_and_clock(self):
        g = detour_table(1, 1, 5).game
        self.assertEqual(optimistic_length(g.board, g.marker, g.goal, 4), 4)
        self.assertIsNone(optimistic_length(g.board, g.marker, g.goal, 3))
        self.assertEqual(optimistic_length(g.board, (0, 1), g.goal, 3), 3)
        self.assertIsNone(optimistic_length(g.board, (1, 0), g.goal, 20))
        self.assertEqual(optimistic_length(g.board, g.goal, g.goal, 0), 0)

    def test_plans_keep_losing_alternatives_and_count_the_pending_discard(self):
        for sx in (-1, 1):
            for sy in (-1, 1):
                state, choices = position(sx, sy)
                menu = plans(state, choices)
                self.assertEqual(state["store_count"], 2)
                self.assertEqual({p["to"] for p in menu if p["steps"] is not None}, {(0, sy)})
                self.assertTrue(any(p["steps"] == 3 for p in menu))
                self.assertTrue(any(p["to"] == (sx, 0) and p["trapped"] for p in menu))
                self.assertTrue(any(p["to"] is None and p["steps"] is None for p in menu))
                # Without a return only two future moves remain.
                self.assertTrue(
                    all(p["steps"] is None for p in plans({**state, "draw_count": 1}, choices))
                )

    @patch(
        "experiments.turn_plans.optimistic_length",
        side_effect=AssertionError("unexpected path search"),
    )
    @patch("experiments.turn_plans.sealed", side_effect=AssertionError("unexpected flood fill"))
    def test_local_plan_cards_use_only_immediate_edges(self, _sealed, _length):
        state, choices = position(1, 1)
        menu = plans(state, choices, local=True)
        self.assertTrue(all(set(p) == {"to", "place", "distance", "edges"} for p in menu))
        self.assertTrue(any(p["to"] == (0, 1) and "E:unbuilt:2" in p["edges"] for p in menu))
        self.assertTrue(any(p["to"] == (1, 0) and not p["edges"] for p in menu))

    @patch("experiments.skill_probe.request")
    def test_card_returns_original_action_and_only_seat_visible_consequences(self, request):
        table = detour_table(-1, -1, 5)
        state = table.game.view(0)
        state["hands"] = ["hidden sentinel"]
        request.return_value = {"message": {"content": '{"action":"south"}'}}
        options = {"to": [(0, -1), (-1, 0), None]}
        self.assertEqual(card_choice(state, options, "test", bound=True), {"to": (0, -1)})
        prompt = request.call_args.args[2]
        self.assertEqual(
            prompt["format"]["properties"]["action"]["enum"], ["south", "west", "wait"]
        )
        self.assertNotIn("sentinel", json.dumps(prompt))
        report = json.loads(prompt["messages"][1]["content"])
        self.assertIn("Still possible", report["available_actions"][0])
        self.assertIn("CERTAIN LOSS", report["available_actions"][1])
        self.assertIn("CERTAIN LOSS", report["available_actions"][2])

    def test_frozen_panel_has_distinct_records_and_all_reflections(self):
        cases = list(positions())
        self.assertEqual(len(cases), 8)
        self.assertEqual(len({name for name, *_ in cases}), 8)
        for _, _, _, choices, targets in cases:
            self.assertTrue(targets <= set(choices["to"]))
