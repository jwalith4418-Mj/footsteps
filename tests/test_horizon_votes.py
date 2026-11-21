import unittest

from experiments.horizon_votes import (
    BUDGET_RULE,
    BudgetSession,
    CountedSession,
    detour,
    fixture,
    seat_session,
)
from footsteps.board import distance
from footsteps.record import replay


class HorizonStudy(unittest.TestCase):
    def test_known_vote_is_pivotal_under_both_rotations(self):
        witness, rev = detour()
        self.assertEqual(replay(witness).winner, "blue")
        self.assertEqual(witness["events"][rev - 1]["kind"], "propose")
        for case, remaining in (("short", 2), ("detour", 5)):
            for heading in ("north", "west"):
                with self.subTest(case=case, heading=heading):
                    g = replay(fixture(case, heading))
                    self.assertEqual(len(g.store), remaining)
                    self.assertEqual(distance(g.pending, g.goal), 3)
                    self.assertEqual(g.pending, (0, 3) if heading == "north" else (-3, 0))

    def test_listener_hears_only_public_remark_and_own_role(self):
        prefix = fixture("short", "west")
        blue = seat_session(prefix, 3, "blue", "An unverified claim.")
        red = seat_session(prefix, 3, "red", "An unverified claim.")
        self.assertEqual(blue.snap["history"], red.snap["history"])
        self.assertEqual(blue.snap["history"][-1]["speaker"], 1)
        self.assertEqual(blue.snap["pieces"], red.snap["pieces"])
        self.assertEqual(blue.role()["team"], "blue")
        self.assertNotIn("red_teammates", blue.role())
        self.assertEqual(red.role()["team"], "red")
        self.assertEqual(blue.snap["choices"], {"vote": [True, False]})
        self.assertEqual(blue.seat.table.votes, {})
        self.assertNotIn("roles", blue.snap["state"])

    def test_budget_rule_only_changes_system_message_even_after_reset(self):
        prefix = fixture("detour", "north")
        base = seat_session(prefix, 3, "blue")
        aided = seat_session(prefix, 3, "blue", session_class=BudgetSession)
        for session in (base, aided):
            session.reset()
        self.assertEqual(
            aided.messages[0]["content"], base.messages[0]["content"] + " " + BUDGET_RULE
        )
        self.assertEqual(aided.messages[1:], base.messages[1:])
        self.assertEqual(aided.tools(), base.tools())

    def test_count_displays_remaining_moves_after_either_ballot_outcome(self):
        for case, count in (("short", 2), ("detour", 5)):
            prefix = fixture(case, "west")
            aided = seat_session(prefix, 3, "blue", session_class=CountedSession)
            base = seat_session(prefix, 3, "blue", session_class=BudgetSession)
            notice = aided.opportunity()
            self.assertEqual(notice.pop("future_movement_opportunities_after_this_ballot"), count)
            self.assertEqual(notice, base.opportunity())
