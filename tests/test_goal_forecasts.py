import unittest
from pathlib import Path
from random import Random

from experiments.action_probe import position
from experiments.goal_pursuit import budget, choices_for, plain_forecast
from footsteps.game import with_exit_origin
from footsteps.table import Table


class GoalForecasts(unittest.TestCase):
    def test_only_the_correct_midpoint_opens_the_two_turn_corridor(self):
        t = Table(
            with_exit_origin(
                {"roles": ["good"], "hands": [[65]], "store": [65, 65], "goal": [0, 2]}
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
