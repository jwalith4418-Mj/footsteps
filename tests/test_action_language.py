import json
import unittest
from pathlib import Path
from random import Random
from unittest.mock import patch

from footsteps.ollama import infer
from footsteps.record import read
from footsteps.seat_tools import blocking_tile, query
from footsteps.table import Table

CROSSING = read(Path(__file__).resolve().parents[1] / "examples/crossing.json")


def crossing(events):
    table = Table(CROSSING["setup"], Random(0))
    table.started = True
    table.opens = 0
    table.deadline = 120
    for event in CROSSING["events"][:events]:
        table.commit(event)
    return table


class ActionLanguage(unittest.TestCase):
    def test_completed_floor_history_excludes_speech_and_unrevealed_votes(self):
        table = crossing(4)
        table.opens = 10
        table.say(1, 4, "P0 stayed three times.", 0)
        table.submit(0, 4, {"vote": False}, 11)
        self.assertEqual(table.view(2, 11)["floor_turns"], [])
        for seat in (1, 2, 3):
            table.submit(seat, 4, {"vote": False}, 11)
        view = table.view(1, 11)
        report = query(view, "check_builder_turns", {"builder": 0})
        self.assertEqual(report["completed_floor_turns"], 1)
        self.assertEqual(
            report["latest_four"],
            [
                {
                    "turn": 1,
                    "builder": 0,
                    "tile_at": (1, 0),
                    "marker_before": (0, 0),
                    "step_requested": (1, 0),
                    "marker_after": (0, 0),
                    "result": "step_rejected",
                }
            ],
        )
        self.assertEqual(query(view, "check_builder_turns", {"builder": 1})["latest_four"], [])
        with self.assertRaises(ValueError):
            query(view, "check_builder_turns", {"builder": 4})
        view.pop("floor_turns")
        with self.assertRaisesRegex(ValueError, "unavailable"):
            query(view, "check_builder_turns", {"builder": 1})

    def test_public_history_distinguishes_step_stay_and_timeout(self):
        for timed_out, expected in [(True, "proposal_timed_out"), (False, "builder_stayed")]:
            table = crossing(3)
            table.commit({"kind": "propose", "to": None, "timeout": timed_out})
            self.assertEqual(table.floor_turns[-1]["result"], expected)
        table = crossing(5)
        self.assertEqual(table.floor_turns[-1]["marker_after"], (1, 0))
        self.assertEqual(table.floor_turns[-1]["result"], "stepped")

    def test_block_requires_no_immediate_step_and_is_scoped_to_next_builders_hand(self):
        state = crossing(4).view(1, 0)
        # When the marker lands on (1,0), its only outgoing side faces unbuilt floor.
        state["state"]["goal"] = (3, 0)
        state["state"]["board"] = [((0, 0), 255), ((1, 0), 40), ((3, 0), 255)]
        state["state"]["hand"] = [15]  # Accepts entry from every side into a dead end.
        self.assertIsNone(
            query(state, "compare_landings", {})["landings"][1]["own_hand_immediate_block"]
        )
        state["state"]["hand"] = [0]
        block = query(state, "compare_landings", {})["landings"][1]["own_hand_immediate_block"]
        self.assertEqual(block, {"tile": 0, "rotation": 0, "at": (2, 0)})
        state["seat"] = 2
        dest = query(state, "compare_landings", {})["landings"][1]
        self.assertEqual(dest["next_builder_if_all_survive"], 1)
        self.assertNotIn("own_hand_immediate_block", dest)
        self.assertIsNone(blocking_tile({(0, 0): 255}, (0, 0), (3, 0), [0]))

    @patch("footsteps.ollama.request")
    def test_named_effects_decode_in_reversed_menu_for_both_adapters(self, request):
        for events, seat, label in [(4, 0, "remain_at_0_0"), (6, 3, "keep_P3")]:
            for social in [False, True]:
                snap = crossing(events).view(seat, 0)
                snap["choices"] = {"vote": [False, True]}

                def first_option(port, path, body, timeout):
                    option = body["format"]["properties"]["vote"]["enum"][0]
                    return {"message": {"content": json.dumps({"vote": option})}}

                request.side_effect = first_option
                choice = infer(
                    snap,
                    "test",
                    10,
                    named_ballots=True,
                    explicit_actions=True,
                    social_guidance=social,
                )
                self.assertEqual(choice, {"vote": False})
                options = request.call_args.args[2]["format"]["properties"]["vote"]["enum"]
                self.assertEqual(options[0].split("__MY_")[0], label)
