import json
import unittest

from experiments.action_probe import position
from experiments.voter_perspective import CASES, ROOT, presentation


class RemovalPerspective(unittest.TestCase):
    def test_relative_view_uses_only_the_voters_granted_knowledge(self):
        source, event = CASES[0]
        for seat, relation in (
            (0, "I was not told the nominee's team."),
            (1, "The nominee is on the other team."),
            (4, "I am the nominee."),
        ):
            with self.subTest(seat=seat):
                snap = position(ROOT / source, event - 1, seat)
                body = presentation(snap, "fixture", True, True, False, True)
                ctx = json.loads(body["messages"][1]["content"])
                self.assertEqual(ctx["my_relationship_to_the_nominee_at_setup"], relation)
                me = ctx["I_am_casting_this_ballot_as"]
                self.assertEqual(me["seat"], f"P{seat}")
                if seat == 1:
                    self.assertEqual(me["all_blue_seats"], ["P0", "P2", "P4"])
                    self.assertEqual(me["all_red_seats"], ["P1", "P3"])
                else:
                    self.assertEqual(set(me), {"seat", "private_team"})
                self.assertEqual(ctx["recent"][-1]["speaker"], "P2")
                self.assertIn("voted to eliminate", ctx["recent"][-1]["public_claim"])
                self.assertNotIn("recorded_event", ctx["recent"][-1])
                subject = "myself" if seat == 4 else "P4"
                self.assertEqual(
                    ctx["options"]["vote"], [f"yes_remove_{subject}", f"no_keep_{subject}"]
                )
