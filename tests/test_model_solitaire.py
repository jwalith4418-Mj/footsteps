import csv
import json
import tempfile
import unittest
from pathlib import Path
from random import Random
from unittest.mock import patch

from experiments.model_solitaire import decide, detour_table, geometry, payload, run_game
from experiments.model_solitaire_audit import audit
from footsteps.record import read
from footsteps.solo import setup
from footsteps.table import Table


class ModelSolitaire(unittest.TestCase):
    def setUp(self):
        self.table = Table(setup(100, (4, 2), 2, 10, 0.55), Random("draw/100"))
        self.table.join(0, 0)

    def test_geometry_preserves_legal_fields_and_uses_the_rotated_entry(self):
        state = self.table.game.view(0)
        choices = self.table.choices(0, 0)
        plain = payload(state, choices, "test")
        aided = payload(state, choices, "test", True)
        self.assertEqual(plain["format"], aided["format"])
        context = json.loads(aided["messages"][1]["content"])
        self.assertTrue({"store", "hands", "roles", "seed", "draw"}.isdisjoint(context))
        east = next(p for p in context["placements_next_to_marker"] if p["at"] == "1,0")
        rotations = {r for face, r, _ in east["enterable_builds"] if face == 163}
        self.assertEqual(rotations, {2, 3})
        self.assertIn(0, context["options"]["rotation"])
        self.assertIn(163, context["options"]["tile"])

    def test_chart_keeps_the_same_literal_menu_and_displays_matching_ports(self):
        table = detour_table(1, 1, 5)
        state = table.game.view(0)
        choices = table.choices(0, 0)
        direct = payload(state, choices, "test")
        charted = payload(state, choices, "test", chart=True)
        self.assertEqual(direct["messages"][0], charted["messages"][0])
        self.assertEqual(direct["format"], charted["format"])
        original, chart = charted["messages"][1]["content"].split("\n\n", 1)
        fields = json.loads(direct["messages"][1]["content"])
        del fields["board"], fields["hand"]
        self.assertEqual(json.loads(original), fields)
        self.assertIn("  1 36  .  .", chart)
        self.assertIn("  0 @S  8  X", chart)
        self.assertIn("8=W>-", chart)
        self.assertIn("36=S>E", chart)
        self.assertIn("Hand: 255 255", chart)
        self.assertEqual(chart.count("255=NESW>NESW"), 1)

    def test_move_aid_distinguishes_sealed_landing_and_open_edge(self):
        state = {
            "board": [((0, 0), 255), ((1, 0), 8), ((0, 1), 36), ((2, 0), 255)],
            "marker": (0, 0),
            "goal": (2, 0),
        }
        options = {"to": [None, (1, 0), (0, 1)]}
        report = geometry(state, options)["landings"]
        self.assertEqual(
            report["1,0"],
            {"distance": 1, "at_EXIT": False, "permanently_trapped": True, "onward": []},
        )
        self.assertFalse(report["0,1"]["permanently_trapped"])
        self.assertEqual(report["0,1"]["onward"], ["E:unbuilt:2"])

    def test_tight_detour_has_a_winning_four_move_continuation(self):
        for sx in (-1, 1):
            for sy in (-1, 1):
                t = detour_table(sx, sy, 5)
                self.assertEqual(t.game.turn, 2)
                self.assertEqual(t.game.view(0)["store_count"], 3)
                t.commit({"kind": "propose", "to": [0, sy]})
                t.commit({"kind": "move_vote", "votes": [True]})
                for at, dest in [
                    ([sx, sy], [sx, sy]),
                    ([2 * sx, sy], [2 * sx, sy]),
                    ([0, 2 * sy], [2 * sx, 0]),
                ]:
                    t.open_decision(0)
                    t.commit({"kind": "place", "at": at, "tile": 255, "rotation": 0})
                    if t.game.stage == "discard":
                        t.commit({"kind": "discard", "tile": 255})
                    t.commit({"kind": "propose", "to": dest})
                    t.commit({"kind": "move_vote", "votes": [True]})
                self.assertEqual(t.game.winner, "blue")
                self.assertEqual(t.game.turn, 5)

    @patch("experiments.model_solitaire.request")
    def test_literal_face_zero_and_boolean_are_distinct(self, mock):
        state = self.table.game.view(0)
        for value in (True, 0):
            mock.return_value = {
                "message": {"content": json.dumps({"tile": value})},
                "done_reason": "length",
            }
            if value is True:
                with self.assertRaises(ValueError):
                    decide(state, {"tile": [0, 1]}, "test")
            else:
                self.assertEqual(decide(state, {"tile": [0, 1]}, "test"), {"tile": 0})

    @patch("experiments.model_solitaire.decide", side_effect=TimeoutError("fixture"))
    def test_failed_decisions_leave_auditable_replay(self, mock):
        with tempfile.TemporaryDirectory() as dest:
            out = Path(dest)
            rows = run_game(100, "fixture", out)
            with (out / "results.csv").open("w") as handle:
                w = csv.writer(handle)
                w.writerow(["seed", "player", "win", "turns", "end_distance", "sealed", "fallback"])
                w.writerows(rows)
            decisions, events = audit(out)
            self.assertEqual(rows[0][-1], decisions)
            self.assertEqual(mock.call_count, decisions)
            record = read(out / "game-100.json")
            self.assertEqual(events, len(record["events"]))
            self.assertEqual(sum(bool(e.get("timeout")) for e in record["events"]), decisions)
