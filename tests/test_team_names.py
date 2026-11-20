import json
import unittest
from pathlib import Path
from random import Random
from unittest.mock import patch

from experiments.social_evidence import social_deal
from experiments.social_prompt import advocate
from footsteps.ollama import infer
from footsteps.record import read, render
from footsteps.table import PAPER_KIT, Table
from footsteps.viewer import transcript

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/crossing.json"


class TeamNames(unittest.TestCase):
    def test_supplemental_seat_preserves_seat_hands_deal_and_clock(self):
        four = social_deal(31, ["good", "bad", "good", "good"], PAPER_KIT)
        roles = ["good", "bad", "good", "bad", "good"]
        five = social_deal(31, roles, PAPER_KIT, paired_fifth_hand=True)
        standard = social_deal(31, roles, PAPER_KIT)
        self.assertCountEqual(sum(standard["hands"], standard["store"].copy()), PAPER_KIT)
        self.assertEqual(len(standard["store"]), 6)
        self.assertEqual(four["hands"], five["hands"][:4])
        self.assertEqual(len(five["hands"][4]), 2)
        self.assertEqual(four["store"], five["store"])
        self.assertEqual(len(five["store"]), 8)

    def test_agent_and_speaker_get_only_their_own_information_in_colors(self):
        record = read(EXAMPLE)
        table = Table(record["setup"], Random(0), discussion=1, color_teams=True)
        table.started = True
        for e in record["events"][:6]:
            table.commit(e)
        table.open_decision(0)
        remark = "Bad luck on the last turn; good luck this turn."
        table.say(0, table.revision, remark, 0)
        for seat in (1, 3):
            snap = table.view(seat, table.opens)
            for stage in ("ordinary", "social", "speaker"):
                with (
                    self.subTest(seat=seat, stage=stage),
                    patch("footsteps.ollama.request") as move,
                    patch("experiments.social_prompt.request") as speech,
                ):
                    if stage == "speaker":
                        speech.return_value = {"message": {"content": '{"statement":"I pass."}'}}
                        advocate(snap, "mock")
                        body = speech.call_args.args[2]
                    else:
                        vote = '"no_keep_myself"' if seat == 3 else '"no_keep_P3"'
                        if stage == "ordinary":
                            vote = "0"
                        move.return_value = {"message": {"content": '{"vote":' + vote + "}"}}
                        infer(snap, "mock", 30, social_guidance=stage == "social")
                        body = move.call_args.args[2]
                    self.assertNotRegex(body["messages"][0]["content"].lower(), r"\b(good|bad)\b")
                    ctx = json.loads(body["messages"][1]["content"])
                    self.assertIn(remark, json.dumps(ctx["recent"]))
                    self.assertIn("Red", ctx["common_knowledge"])
                    private = ctx["your_private_role_information"]
                    if seat == 3:
                        self.assertEqual(private["all_red_seats"], [3])
                        self.assertEqual(private["all_blue_seats"], [0, 1, 2])
                    else:
                        self.assertEqual(private, {"seat": 1, "alignment": "Blue"})

    def test_replay_names_preserve_records_and_public_words(self):
        record = read(EXAMPLE)
        record["team_names"] = "colors"
        record["remarks"] = [{"after_event": 4, "seat": 3, "text": "That was a good move."}]
        data = transcript(record, 0)
        self.assertEqual(data["team_labels"], {"good": "Blue", "bad": "Red"})
        self.assertEqual(data["frames"][4]["remarks"][0]["text"], "That was a good move.")
        self.assertIn("Winner: **Blue**", render(record))
        self.assertIn("P3 Red", render(record))
        self.assertEqual(record["setup"]["roles"][3], "bad")
