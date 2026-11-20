import json
import unittest
from pathlib import Path
from random import Random

from experiments.social_prompt import progress_ballots
from footsteps.game import with_exit_origin
from footsteps.record import new_record, read, render, replay
from footsteps.table import Table
from footsteps.viewer import transcript

CROSSING = Path(__file__).resolve().parents[1] / "examples/crossing.json"


class ExitOrigin(unittest.TestCase):
    def test_shared_frame_from_setup_to_final_vote(self):
        crossing = read(CROSSING)
        table = Table(with_exit_origin(crossing["setup"]), Random(0))
        self.assertEqual(table.record["format"], 3)
        table.started = True
        for event in crossing["events"]:
            event = event.copy()
            for field in ("at", "to"):
                if event.get(field) is not None:
                    x, y = event[field]
                    event[field] = [x - 2, y]
            if event["kind"] == "place":
                self.assertIn(tuple(event["at"]), table.choices(table.game.actor, 0)["at"])
                self.assertNotIn((0, 0), table.choices(table.game.actor, 0)["at"])
            table.commit(event)
        snap = table.view(1, 0)
        self.assertEqual((snap["state"]["start"], snap["state"]["marker"]), ((-2, 0), (0, 0)))
        vote = progress_ballots(snap)[0]
        self.assertEqual((vote["from_distance"], vote["to_distance"]), (2, 1))
        self.assertEqual(replay(table.record).winner, "blue")
        self.assertIn("Start (-2, 0), goal (0, 0)", render(table.record))
        for seat in (None, 1):
            view = transcript(table.record, seat)
            self.assertEqual((view["start"], view["goal"]), (("-2", "0"), ("0", "0")))
            self.assertEqual(view["frames"][0]["marker"], view["start"])
            self.assertEqual(view["frames"][4]["pending"], ("-1", "0"))
        self.assertNotIn("hands", json.dumps(transcript(table.record)))

    def test_format_selects_the_coordinate_contract(self):
        legacy = json.loads((Path(__file__).parent / "fixtures/crossing-v1.json").read_text())
        legacy["setup"]["start"] = [10, -20]  # Previously ignored extra metadata.
        self.assertEqual(replay(legacy).start, (0, 0))
        self.assertEqual(transcript(legacy)["start"], ("0", "0"))
        missing = {
            **legacy,
            "format": 2,
            "setup": {k: v for k, v in legacy["setup"].items() if k != "start"},
        }
        with self.assertRaisesRegex(ValueError, "explicit start"):
            replay(missing)
        setup = read(CROSSING)["setup"] | {"start": [2, 0]}
        with self.assertRaisesRegex(ValueError, "must differ"):
            replay(new_record(setup))
        with self.assertRaisesRegex(ValueError, "coordinate"):
            replay(new_record(setup | {"start": [True, False]}))
