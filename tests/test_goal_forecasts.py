import json
import unittest
from pathlib import Path
from random import Random
from unittest.mock import patch

from experiments.action_probe import position
from experiments.goal_pursuit import budget, choices_for, decide, plain_forecast
from footsteps.game import with_exit_origin
from footsteps.table import Table


class GoalForecasts(unittest.TestCase):
    def test_public_exit_ballot_outcomes_are_the_same_for_both_teams(self):
        p = (
            Path(__file__).resolve().parents[1]
            / "experiments/goal-pursuit/games/four-9501-brief.json"
        )
        for seat, team in [(1, "Red"), (2, "Blue")]:
            for remaining, stay_result in [(1, "play continues"), (0, "Red wins")]:
                with self.subTest(seat=seat, remaining=remaining):
                    snap = position(p, 71, seat)
                    snap["state"]["store_count"] = remaining
                    with patch("experiments.goal_pursuit.request") as request:
                        request.return_value = {
                            "message": {"content": '{"choice":"remain_at_1_0","reason":"Stay."}'}
                        }
                        choice = decide(snap, "fixture", None, [], arm="clear", order=Random(1))
                    self.assertEqual(choice, {"vote": False})
                    messages = request.call_args.args[2]["messages"]
                    ctx = json.loads(messages[1]["content"])
                    self.assertEqual(
                        (ctx["voter"], ctx["team"], ctx["step_proposed_by"]),
                        (f"P{seat}", team, "P2"),
                    )
                    self.assertEqual(
                        {k: v["game_result"] for k, v in ctx["candidates"].items()},
                        {"step_to_0_0": "Blue wins", "remain_at_1_0": stay_result},
                    )

    def test_only_the_correct_midpoint_opens_the_two_turn_corridor(self):
        t = Table(
            with_exit_origin(
                {"roles": ["blue"], "hands": [[65]], "store": [65, 65], "goal": [0, 2]}
            ),
            Random(0),
        )
        t.join(0, 0)
        snap = t.view(0, 0)
        self.assertEqual(budget(snap["state"]), 1)
        choices = choices_for(snap)
        possible = [a for a, report in choices if any(n is not None for _, n, _ in report)]
        self.assertEqual(possible, [{"at": [0, -1], "tile": 65, "rotation": 2}])
        t.submit(0, t.revision, possible[0], 0)
        t.submit(0, t.revision, {"tile": 65}, 0)
        t.submit(0, t.revision, {"to": [0, -1]}, 0)
        t.submit(0, t.revision, {"vote": True}, t.opens)
        self.assertEqual(budget(t.view(0, t.opens)["state"]), 0)

    def test_ballot_back_to_start_keeps_the_only_route_in_time(self):
        p = (
            Path(__file__).resolve().parents[1]
            / "experiments/native-actions/games/9501-hand-all.json"
        )
        reports = []
        for seat in (0, 1):
            snap = position(p, 15, seat)
            rows = choices_for(snap)
            reports.append(rows)
            self.assertEqual(rows[0], ({"vote": True}, (((-2, -2), 6, False),)))
            self.assertEqual(rows[1], ({"vote": False}, (((-1, -2), None, False),)))
            self.assertIn("No landing", plain_forecast(rows[1][1]))
        self.assertEqual(reports[0], reports[1])
