import unittest

from experiments.rana_speakers import position
from footsteps.viewer import transcript


class SpeakerPositions(unittest.TestCase):
    def test_matched_challenges_change_only_private_information(self):
        for focal in (2, 3):
            red, red_session = position(focal, "red", True)
            blue, blue_session = position(focal, "blue", True)
            self.assertEqual(transcript(red.table.record), transcript(blue.table.record))
            self.assertEqual(red_session.role()["team"], "red")
            self.assertEqual(blue_session.role()["team"], "blue")
            self.assertNotIn("red_teammates", blue_session.role())
            self.assertEqual(red_session.snap["state"]["pending"], focal)
            self.assertTrue(red_session.snap["can_speak"])

    def test_hand_question_precedes_draw_and_is_identical_for_blank_and_connector(self):
        blank, bs = position(1, "red", True, 0)
        full, fs = position(1, "red", True, 255)
        self.assertEqual(transcript(blank.table.record), transcript(full.table.record))
        self.assertEqual(bs.snap["pieces"], {"H1": [0, 0]})
        self.assertEqual(fs.snap["pieces"], {"H1": [255, 0]})
        self.assertEqual(bs.snap["history"][-1]["speaker"], 2)
        self.assertEqual(bs.snap["state"]["pending"], 1)
