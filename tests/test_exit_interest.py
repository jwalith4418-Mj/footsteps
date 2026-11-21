import json
import unittest
from unittest.mock import patch

from experiments.exit_interest import CASES, conditions, prefix, seat, trap, trial
from footsteps.board import moves
from footsteps.record import replay


class ExitInterest(unittest.TestCase):
    def test_a_closer_step_strands_the_marker_and_rejection_has_a_winning_witness(self):
        floor = prefix("trap")
        game = replay(floor)
        game.apply({"kind": "move_vote", "votes": [True] * 5})
        self.assertIsNone(game.winner)
        self.assertEqual(game.board[game.marker] >> 4, 0)
        self.assertEqual(moves(game.board, game.marker), [])
        self.assertEqual(replay(trap()).winner, "blue")

    def test_blue_cannot_see_a_proposers_hidden_card_change(self):
        for case in CASES:
            builder = replay(prefix(case)).actor
            blue = [
                seat(case, v, rs) for v, rs in conditions(case) if v != builder and rs[v] == "blue"
            ]
            with self.subTest(case=case):
                self.assertEqual(len(blue), 2)
                a, b = blue
                self.assertEqual(a.messages, b.messages)
                self.assertEqual(a.opportunity(), b.opportunity())
                self.assertEqual(a.snap["history"], b.snap["history"])
                self.assertNotEqual(
                    a.seat.table.game.roles[builder], b.seat.table.game.roles[builder]
                )

    def test_forecast_forks_before_the_ballot_and_has_no_sealed_choice(self):
        voter, roles = next(conditions("13401"))

        def vote(port, path, body, budget):
            return {
                "message": {
                    "tool_calls": [
                        {"function": {"name": "vote_move", "arguments": {"approve": True}}}
                    ]
                }
            }

        with (
            patch("experiments.exit_interest.request", side_effect=vote),
            patch("experiments.exit_interest.question", return_value={}) as forecast,
        ):
            row = trial("13401", voter, roles, "test")
        self.assertTrue(row["vote"])
        messages = forecast.call_args.args[0]
        self.assertEqual(json.loads(messages[-1]["content"])["stage"], "move_vote")
        self.assertFalse(any(m["role"] in {"tool", "assistant"} for m in messages))
