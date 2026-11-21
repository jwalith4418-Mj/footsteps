import io
import json
import tempfile
import unittest
from pathlib import Path
from random import Random
from unittest.mock import Mock

from experiments.persistent_guest import LiveGuest
from footsteps.ollama import ServiceError
from footsteps.record import read
from footsteps.table import Table


class PersistentGuest(unittest.TestCase):
    def test_late_response_cannot_be_applied_to_a_later_revision_or_saved_as_accepted(self):
        fixture = read(Path(__file__).resolve().parents[1] / "examples/crossing.json")
        table = Table(fixture["setup"], Random(5), discussion=0)
        for i in range(4):
            table.join(i, 0)
        fresh = table.view(0, 0) | {"table_id": "test"}
        with tempfile.TemporaryDirectory() as tmp:
            guest = LiveGuest(Path(tmp), 0, Path(tmp) / "debrief.md")
            seen = []

            def choose(kind, snap, *, timeout):
                seen.append((kind, snap["revision"]))
                return {
                    "choice": {
                        "tile": fresh["choices"]["tile"][0],
                        "at": fresh["choices"]["at"][0],
                        "rotation": 0,
                    },
                    "observation": "test",
                }

            guest.ask = Mock(side_effect=choose)
            guest.finish = Mock()
            peer = Mock()
            next_rev = fresh | {"revision": fresh["revision"] + 1}
            peer.call.side_effect = [
                fresh,
                ServiceError(409, "closed"),
                next_rev,
                {},
                fresh | {"phase": "over"},
            ]
            notes = io.StringIO()
            guest.play(peer, notes)
            self.assertEqual(
                seen, [("choice", fresh["revision"]), ("choice", next_rev["revision"])]
            )
            self.assertEqual(json.loads(notes.getvalue())["revision"], next_rev["revision"])
            self.assertEqual(json.loads(notes.getvalue())["table_id"], "test")

    def test_an_unanswered_timed_packet_expires_and_can_be_skipped(self):
        fixture = read(Path(__file__).resolve().parents[1] / "examples/crossing.json")
        table = Table(fixture["setup"], Random(0))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            guest = LiveGuest(root, 0, root / "debrief.md")
            table.join(0, 0)
            snap = table.view(0, 0)
            snap["history"] = [{"text": "still owed after a missed packet"}]
            self.assertIsNone(guest.ask("speech", snap, timeout=0))
            self.assertEqual(guest.history_count, 0)
            guest.finish(snap, timeout=0)
            self.assertEqual(
                json.loads((root / "0002.request.json").read_text())["new_history"], snap["history"]
            )
            self.assertTrue((root / "0001.expired").exists())
            self.assertTrue((root / "finished").exists())
            self.assertFalse(guest.debrief_path.exists())
