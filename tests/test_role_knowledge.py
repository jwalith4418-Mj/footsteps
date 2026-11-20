import json
import unittest
from copy import deepcopy
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
from unittest.mock import patch

from experiments.social_evidence import social_game
from experiments.social_prompt import advocate
from footsteps.ollama import model_request
from footsteps.role_knowledge import COMMON_KNOWLEDGE, role_information
from footsteps.social import social_request
from footsteps.table import Table


def seat_view(roles, seat):
    table = Table(
        {"goal": [4, 2], "roles": roles, "hands": [[8] for _ in roles], "store": [16, 32]},
        Random(0),
    )
    for event in (
        {"kind": "draw", "tiles": [16, 32]},
        {"kind": "place", "at": [1, 0], "tile": 8, "rotation": 0},
        {"kind": "discard", "tile": 16},
        {"kind": "propose", "to": None},
        {"kind": "nominate", "target": 3},
        {"kind": "eliminate_vote", "votes": [True] * 4},
    ):
        table.commit(event)
    return table.view(seat, 0)


class RoleKnowledge(unittest.TestCase):
    def test_same_public_rule_and_distinct_private_grants(self):
        roles = ["bad", "good", "good", "bad"]
        bad = seat_view(roles, 0)
        good = seat_view(roles, 1)
        lone_bad = seat_view(["bad", "good", "good", "good"], 0)
        for snap in (bad, good, lone_bad):
            briefing = role_information(snap)["common_knowledge"]
            self.assertEqual(briefing, COMMON_KNOWLEDGE)
            for rule in ("every seat sees each remark", "either team may", "lie", "no extra"):
                self.assertIn(rule, briefing)
        self.assertNotIn(3, bad["state"]["alive"])
        self.assertEqual(
            role_information(bad)["your_private_role_information"],
            {"seat": 0, "alignment": "bad", "all_bad_seats": [0, 3], "all_good_seats": [1, 2]},
        )
        self.assertEqual(
            role_information(lone_bad)["your_private_role_information"]["all_good_seats"], [1, 2, 3]
        )
        self.assertEqual(
            role_information(good)["your_private_role_information"],
            {"seat": 1, "alignment": "good"},
        )

    def test_good_prompts_are_identical_after_hidden_swap(self):
        # P2 is the next nominator. Every public action, including P3's removal, is unchanged.
        roles = ["bad", "good", "good", "bad"]
        swapped = ["good", "bad", "good", "bad"]

        def requests(roles):
            snap = seat_view(roles, 2)
            snap["choices"] = {"target": [None, 0, 1]}
            standard = model_request(snap, "test")
            guided = deepcopy(standard)
            social_request(guided, snap, explain=False)
            with patch(
                "experiments.social_prompt.request",
                return_value={"message": {"content": '{"statement":"I pass."}'}},
            ) as mock:
                advocate(snap, "test")
                speech = mock.call_args.args[2]
            for body in (standard, guided, speech):
                context = json.loads(body["messages"][1]["content"])
                self.assertEqual(context["common_knowledge"], COMMON_KNOWLEDGE)
                self.assertNotIn("all_bad_seats", context["your_private_role_information"])
            return standard, guided, speech

        self.assertEqual(requests(roles), requests(swapped))

    def test_four_seat_table_gives_allies_their_private_map(self):
        maps = {}

        def decide(snap, *args, **kwargs):
            maps[snap["seat"]] = role_information(snap)["your_private_role_information"]
            return {k: v[0] for k, v in snap["choices"].items()}

        with (
            TemporaryDirectory() as tmp,
            patch("experiments.social_evidence.infer", side_effect=decide),
        ):
            root = Path(tmp)
            rows = social_game(
                8601,
                ["good", "bad", "good", "bad"],
                "mock",
                root / "game.json",
                root / "notes.jsonl",
                "receipt",
                debate=True,
                model_floor=True,
                outcome_policy=True,
            )
            self.assertTrue(rows)
            self.assertTrue(all(r["bad"] == "1+3" for r in rows))
            self.assertEqual(maps[1]["all_bad_seats"], [1, 3])
            self.assertEqual(maps[3]["all_good_seats"], [0, 2])
            self.assertNotIn("all_bad_seats", maps[0])

    def test_speaker_receives_valid_bad_map_without_publishing_it(self):
        snap = seat_view(["bad", "good", "good", "bad"], 0)
        with patch(
            "experiments.social_prompt.request",
            return_value={"message": {"content": '{"statement":"Watch the east door."}'}},
        ) as mock:
            self.assertEqual(advocate(snap, "test"), "Watch the east door.")
            context = json.loads(mock.call_args.args[2]["messages"][1]["content"])
        self.assertEqual(context["your_private_role_information"]["all_bad_seats"], [0, 3])
        self.assertEqual(context["initial_bad"], 2)
