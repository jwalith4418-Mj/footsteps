"""The embedded data is the privacy boundary of a shared offline transcript."""

import json
import unittest
from pathlib import Path

from footsteps.record import read
from footsteps.viewer import export_html, transcript

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/crossing.json"


class TranscriptViewer(unittest.TestCase):
    def test_public_prefix_and_ballot(self):
        r = read(EXAMPLE)
        r["events"] = r["events"][:5]
        frames = transcript(r)["frames"]
        for f in frames:
            self.assertTrue({"hand", "hands", "role", "roles", "teammates", "store"}.isdisjoint(f))
        self.assertNotIn("18", frames[1]["message"])
        self.assertNotIn("18", frames[3]["message"])
        self.assertEqual(frames[2]["placed"], [("1", "0"), 40, 40, 0])
        self.assertEqual(frames[4]["pending"], ("1", "0"))
        self.assertEqual(frames[4]["marker"], ("0", "0"))
        self.assertEqual(frames[5]["marker"], ("1", "0"))
        self.assertEqual(frames[5]["ballots"], [(0, True), (1, True), (2, None), (3, False)])
        self.assertIsNone(frames[-1]["winner"])

    def test_public_discussion_on_pending_ballot_including_open_prefix(self):
        record = read(EXAMPLE)
        record["events"] = record["events"][:4]
        record["remarks"] = [
            {"after_event": 4, "seat": 1, "text": "</script> Watch the exit.", "extra": "hidden"},
            {"after_event": 4, "seat": 2, "text": "I agree."},
        ]
        for perspective in ({}, {"seat": 0}, {"omniscient": True}):
            frames = transcript(record, **perspective)["frames"]
            self.assertFalse(any("remarks" in f for f in frames[:-1]))
            self.assertEqual(
                frames[-1]["remarks"],
                [
                    {"seat": 1, "text": "</script> Watch the exit."},
                    {"seat": 2, "text": "I agree."},
                ],
            )
        self.assertNotIn("</script> Watch", export_html(record, "Trial"))
        for revision in (-1, 3, 5):
            record["remarks"][0]["after_event"] = revision
            with self.assertRaises(ValueError):
                transcript(record)

    def test_perspective_across_elimination_and_reveal(self):
        r = read(EXAMPLE)
        data = transcript(r, 3)
        self.assertNotIn("setup", data)
        self.assertNotIn("events", data)
        frames = data["frames"]
        self.assertEqual(frames[0]["hand"], [0])
        self.assertEqual(frames[0]["role"], "red")
        self.assertNotIn("18", frames[1]["message"])
        self.assertNotIn(3, frames[7]["alive"])
        self.assertNotIn("roles", frames[-2])
        self.assertEqual(frames[-1]["roles"], r["setup"]["roles"])
        self.assertEqual(transcript(r, 0)["frames"][1]["hand"], [40, 18, 12])

    def test_hands_at_each_event_and_export_boundaries(self):
        record = read(EXAMPLE)
        for hand in record["setup"]["hands"]:
            hand.append(18)
        referee = transcript(record, omniscient=True)["frames"]
        player = transcript(record, 0)["frames"]
        public = transcript(record)["frames"]
        self.assertEqual(
            [f["hands"][0] for f in referee[:4]],
            [[40, 18], [40, 18, 18, 12], [18, 18, 12], [18, 12]],
        )
        for i, frame in enumerate(referee):
            self.assertEqual(frame["hands"][0], player[i]["hand"])
            self.assertNotIn("hands", player[i])
            self.assertTrue({"hands", "hand"}.isdisjoint(public[i]))
            self.assertEqual(frame["roles"], record["setup"]["roles"])
        self.assertNotIn(3, referee[7]["alive"])
        self.assertEqual(referee[7]["hands"][3], [0, 18])
        self.assertIn("returned 18", referee[3]["message"])
        self.assertIn("[18]", referee[10]["message"])
        self.assertNotIn("[18]", player[10]["message"])
        with self.assertRaisesRegex(ValueError, "choose a seat"):
            transcript(record, 0, omniscient=True)

    def test_export_setup_only_and_html_delimiters(self):
        r = read(EXAMPLE)
        r["events"].clear()
        r["setup"]["goal"] = [2**60 + 1, -1]
        title = "</script><script>alert(1)</script>"
        page = export_html(r, title)
        self.assertNotIn(title, page)
        payload = page.split('type="application/json">', 1)[1].split("</script>", 1)[0]
        data = json.loads(payload)
        self.assertEqual(data["title"], title)
        self.assertEqual(data["goal"][0], str(2**60 + 1))
        self.assertEqual(len(data["frames"]), 1)
        with self.assertRaisesRegex(ValueError, "invalid seat"):
            export_html(r, "test", -1)

    def test_referee_rejects_invalid_history(self):
        r = read(EXAMPLE)
        r["events"][3]["to"] = [0, 1]
        with self.assertRaisesRegex(ValueError, "event 4"):
            transcript(r)
