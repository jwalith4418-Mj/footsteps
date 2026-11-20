import unittest

from experiments.placement_audit import audit
from footsteps.record import new_record


class PlacementAudit(unittest.TestCase):
    def setUp(self):
        self.record = new_record({"roles": ["good"], "goal": [2, 0], "hands": [[]], "store": [0]})
        self.record.update(table_id="trial", placement_check="edge-and-marker")
        self.build = {"tile": 0, "rotation": 0, "at": [1, 0]}
        self.record["events"] = [
            {"kind": "draw", "tiles": [0]},
            {"kind": "place", **self.build},
            {"kind": "propose", "to": None},
        ]
        self.answer = {**self.build, "origin": [0, 0], "can_step": False, "marker_on_origin": True}

    def test_score_uses_floor_before_build_and_only_first_answer(self):
        log = {
            "turn": 1,
            "attempts": [(self.answer | {"marker_on_origin": False}, "wrong"), (self.answer, None)],
        }
        (row,) = audit(self.record, [log])
        self.assertFalse(row["edge_open"])
        self.assertTrue(row["first_edge_correct"])
        self.assertFalse(row["first_marker_correct"])
        self.assertEqual(row["retry_subject"], "same")

    def test_unanswered_fallback_is_unscored_and_mismatched_log_rejected(self):
        self.record["events"][1]["timeout"] = True
        log = {"turn": 1, "attempts": [], "fallback": "deadline"}
        (row,) = audit(self.record, [log])
        self.assertIsNone(row["first_edge_correct"])
        self.assertIsNone(row["first_marker_correct"])
        self.assertTrue(row["fallback"])
        with self.assertRaisesRegex(ValueError, "does not match"):
            list(audit(self.record, [log | {"table_id": "other"}]))
