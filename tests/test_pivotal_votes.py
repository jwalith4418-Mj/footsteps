import json
import unittest

from experiments.pivotal_votes import ballot, finish, prompt
from footsteps.record import replay


class PivotalVotes(unittest.TestCase):
    def test_roster_swap_changes_the_winning_vote_on_identical_public_floors(self):
        for panel in ("east", "north", "wrap"):
            with self.subTest(panel=panel):
                blue, observer = ballot(panel, "blue")
                red, other_observer = ballot(panel, "red")
                self.assertEqual(observer, other_observer)
                self.assertEqual(blue.game.view(), red.game.view())
                self.assertEqual(blue.record["events"], red.record["events"])
                for table, yes in ((blue, True), (red, False)):
                    for vote in (False, True):
                        actor, winner, record = finish(table, observer, vote)
                        self.assertEqual(winner, "red" if vote == yes else "blue")
                        self.assertEqual(replay(record).winner, winner)
                        self.assertEqual(actor == table.game.pending, not vote)
                    self.assertEqual(table.game.stage, "eliminate_vote")

    def test_visible_forecast_respects_private_knowledge_and_reversed_vote_order(self):
        table, observer = ballot("wrap", "blue")
        for seat in (table.game.pending, observer):
            snap = table.view(seat, table.opens)
            snap["choices"]["vote"] = [False, True]
            body = prompt(snap, "fixture", "inline-team")
            ctx = json.loads(body["messages"][1]["content"])
            rows = ctx["my_ballot_options"]
            self.assertEqual([r["my_vote"] for r in rows], [False, True])
            self.assertEqual([r["last_builder"] for r in rows], ["P4", "P0"])
            self.assertEqual(
                [r["last_builder_team_known_to_me"] for r in rows],
                ["blue", "red" if seat == observer else "undisclosed"],
            )
            self.assertNotIn("expected_vote", ctx)
            self.assertNotIn("outcomes", ctx)

    def test_fixed_programs_can_make_protecting_the_same_teammate_lose(self):
        table, observer = ballot("wrap", "red")
        self.assertEqual(table.game.roles[observer], table.game.roles[table.game.pending])
        for nominee_steps in (False, True):
            controllers = {4: nominee_steps, 0: not nominee_steps}
            for vote in (False, True):
                _, winner, _ = finish(table, observer, vote, controllers)
                self.assertEqual(winner, "red" if vote == nominee_steps else "blue")
