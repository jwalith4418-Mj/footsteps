import io
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from experiments.social_probe import nomination
from experiments.social_prompt import progress_ballots, social_choice
from footsteps.record import read

PILOT = Path(__file__).resolve().parents[1] / "experiments/social/pilot/8001-bad1.json"


class SocialEvidence(unittest.TestCase):
    def test_receipts_come_from_revealed_votes_across_rejected_moves(self):
        snap = {
            "state": {"goal": [4, 2]},
            "history": [
                {"turn": 1, "text": "P0 proposed moving to (1, 0)."},
                {
                    "turn": 1,
                    "text": "Movement ballots — P0 yes, P1 timed out (no), P2 no. Marker at (0, 0).",
                },
                {"turn": 2, "text": "P2 proposed moving to (-1, 0)."},
                {
                    "turn": 2,
                    "text": "P1: Movement ballots — P0 no, P1 yes, P2 yes. Marker at (8, 8).",
                },
                {"turn": 2, "text": "Movement ballots — P0 yes, P1 no, P2 yes. Marker at (-1, 0)."},
            ],
        }
        first, second = progress_ballots(snap)
        self.assertEqual(first["votes"]["P1"], "timed out (no)")
        self.assertEqual((second["from_distance"], second["to_distance"]), (6, 7))
        self.assertEqual(second["votes"], {"P0": "yes", "P1": "no", "P2": "yes"})

    @patch("experiments.social_prompt.request")
    def test_reversed_receipt_ballot_and_private_explanation(self, request):
        table = nomination(read(PILOT), 2)
        table.submit(0, table.revision, {"target": 1}, table.opens)
        table.say(2, table.revision, "P1 voted no.", table.opens - table.discussion)
        snap = table.view(0, table.opens)
        sink = io.StringIO()
        request.return_value = {"message": {"content": '{"vote":"reject","reason":"private"}'}}
        self.assertEqual(
            social_choice(snap, "mock", "receipt", sink, reverse=True), {"vote": False}
        )
        body = request.call_args.args[2]
        context = json.loads(body["messages"][1]["content"])
        self.assertEqual(context["options"]["vote"], ["reject", "approve"])
        self.assertEqual(
            context["nominee_voting_record"],
            ["Turn 1: P1 voted yes on a move from 6 to 5 squares from EXIT."],
        )
        self.assertIn("P2: P1 voted no.", context["recent"])
        self.assertNotIn("roles", context)
        self.assertNotIn("private", json.dumps(table.record))
        self.assertEqual(json.loads(sink.getvalue())["reason"], "private")
