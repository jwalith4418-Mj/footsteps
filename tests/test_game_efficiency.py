import json
import unittest
from collections import defaultdict
from pathlib import Path
from unittest.mock import Mock, patch

from experiments.efficiency_audit import reserve_audit
from experiments.game_efficiency import IdleBudgetSession, RepeatAwareSession
from experiments.persistent_panel import corridor
from experiments.persistent_proposals import FixtureSeat
from experiments.return_recovery import prepared
from experiments.team_objective import ballot
from footsteps.record import read


class EfficiencyStudy(unittest.TestCase):
    def test_read_receipt_is_scoped_to_query_cursor_and_context(self):
        peer = FixtureSeat(corridor("east"))
        session = RepeatAwareSession(peer)

        def call(name, **args):
            return session.execute(name, args, session.tools(), session.snap["revision"])

        self.assertIn("held", call("get_state"))
        self.assertIn("place_tile", call("get_state")["available_commit_tools"])
        call("get_role")
        self.assertIn("held", call("get_state"))
        session.reset()
        self.assertIn("held", call("get_state"))
        call("place_tile", piece="H1", x=-1, y=0)
        self.assertIn("held", call("get_state"))
        self.assertIn("return_tile", call("get_state")["available_commit_tools"])

    def test_frozen_return_comparison_changes_only_the_last_error(self):
        control = prepared(6, False)
        named = prepared(6, True)
        self.assertEqual(control.messages[:-1], named.messages[:-1])
        a, b = (json.loads(s.messages[-1]["content"]) for s in (control, named))
        self.assertIn("return_tile", b.pop("error"))
        self.assertNotIn("return_tile", a.pop("error"))
        self.assertEqual(a, b)

    def test_objective_arms_keep_sealed_ballots_and_same_seat_projection(self):
        control, named = (ballot(1, "red", arm, remarks=True) for arm in ("control", "named-team"))
        self.assertEqual(control.messages[1:], named.messages[1:])
        self.assertIn("for Red to win", named.messages[0]["content"])
        self.assertFalse(named.snap["voted"])
        self.assertEqual(named.snap["choices"], {"vote": [True, False]})
        self.assertEqual(named.snap["history"][-1]["speaker"], 0)
        self.assertNotIn("votes", named.snap)
        other = ballot(0, "blue", "objective")
        self.assertNotIn("red_teammates", other.role())
        self.assertEqual(len(control.snap["history"]), len(other.snap["history"]) + 2)

    def test_idle_budget_defers_inference_until_a_visible_change(self):
        session = IdleBudgetSession.__new__(IdleBudgetSession)
        session.cursor = 1
        session.snap = {"phase": "decision", "choices": None, "can_speak": False}
        session.refresh = Mock()
        session.wait = Mock()

        with patch("footsteps.session.Session.step", return_value="inferred") as step:
            self.assertEqual(session.step("mock"), "inferred")
            self.assertIsNone(session.step("mock"))
            session.wait.assert_called_once_with(1)
            session.cursor += 1
            self.assertEqual(session.step("mock"), "inferred")
            session.snap["can_speak"] = True
            self.assertEqual(session.step("mock"), "inferred")
            session.snap.update(can_speak=False, choices={"vote": [True, False]})
            self.assertEqual(session.step("mock"), "inferred")
            self.assertEqual(step.call_count, 4)

    def test_reserve_refills_on_new_turn_and_excludes_waiting_for_peers(self):
        record = read(Path(__file__).resolve().parents[1] / "examples/crossing.json")
        calls = defaultdict(list)

        def add(seat, revision, service, queue=0):
            calls[seat, revision].append(
                {
                    "tool": "get_state",
                    "opportunity": {"owe_action": True, "seconds_left_in_phase": 45},
                    "queue_seconds": queue,
                    "inference_seconds": service + queue,
                }
            )

        add(0, 1, 22, 10)
        add(0, 2, 1, 38)
        add(1, 4, 16)
        outcomes = list(reserve_audit(record, calls, base=15, cap=30, refill=3))
        by_key = {(o["seat"], o["rev"]): o for o in outcomes}
        self.assertEqual(by_key[0, 1]["reserve_after"], 23)
        self.assertEqual(by_key[0, 2]["reserve_after"], 23)
        self.assertEqual(by_key[1, 4]["reserve_before"], 30)
        next_turn = next(o for o in outcomes if o["turn"] == 2 and o["seat"] == 0)
        self.assertEqual(next_turn["reserve_before"], 26)
