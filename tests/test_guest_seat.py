import json
import tempfile
import unittest
from pathlib import Path
from random import Random
from unittest.mock import Mock, patch

from experiments.guest_game import Guest
from experiments.social_evidence import social_game
from footsteps.decision_notes import read_notes
from footsteps.record import read
from footsteps.table import Table
from footsteps.viewer import transcript

CROSSING = read(Path(__file__).resolve().parents[1] / "examples/crossing.json")


def packet(guest, table, kind):
    seq = guest.sequence + 1
    (guest.root / f"{seq:04}.reply.json").write_text('{"observation":"ready"}')
    snap = table.view(guest.seat, 0)
    if kind == "debrief":
        guest.finish(snap)
    else:
        guest.ask(kind, snap)
    return json.loads((guest.root / f"{seq:04}.request.json").read_text())


class GuestSeat(unittest.TestCase):
    def test_guest_build_notes_attach_to_the_record(self):
        def first(snap, *args, **kwargs):
            return {k: choices[0] for k, choices in snap["choices"].items()}

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("experiments.social_evidence.infer", first),
        ):
            root = Path(tmp)
            guest = Guest(root, 0, root / "debrief.md")
            guest.ask = Mock(
                side_effect=lambda kind, snap: {
                    "choice": first(snap) if snap["choices"] else {},
                    "observation": "test",
                }
            )
            guest.finish = Mock()
            social_game(
                1,
                ["good", "bad", "good"],
                "fixture",
                root / "game.json",
                root / "notes.jsonl",
                "receipt",
                debate=True,
                model_floor=True,
                outcome_policy=True,
                guest=guest,
            )
            notes = read_notes([root / "notes.jsonl"])
            self.assertTrue({"place", "propose", "discard"} <= {r["stage"] for r in notes})
            frames = transcript(read(root / "game.json"), omniscient=True, notes=notes)["frames"]
            self.assertTrue(all(n["matches"] for f in frames for n in f.get("decision_notes", [])))

    def test_guest_receives_only_private_seat_and_incremental_history_even_at_reveal(self):
        for seat in (0, 3):
            table = Table(CROSSING["setup"], Random(0), color_teams=True)
            with self.subTest(seat=seat), tempfile.TemporaryDirectory() as tmp:
                exchange = Path(tmp)
                guest = Guest(exchange, seat, exchange / "debrief.md")

                setup = packet(guest, table, "arrival")
                self.assertNotIn("roles", setup)
                self.assertNotIn("store", setup)
                self.assertNotIn("hands", setup)
                self.assertEqual([t[0] for t in setup["hand"]], CROSSING["setup"]["hands"][seat])
                self.assertEqual("other_red_seats" in setup, seat == 3)
                for event in CROSSING["events"][:4]:
                    table.commit(event)
                table.started = True
                table.open_decision(0)
                table.say(1, table.revision, "I intend to vote yes.", 0)
                ballot = packet(guest, table, "speech")
                self.assertTrue(any("P1: I intend" in e["text"] for e in ballot["new_history"]))
                for event in CROSSING["events"][4:]:
                    table.commit(event)
                self.assertTrue(table.game.winner)
                end = packet(guest, table, "debrief")
                self.assertEqual(guest.debrief_path.read_text(), "ready\n")
                self.assertTrue((exchange / "finished").is_file())
                self.assertTrue(
                    {"role", "roles", "winner", "hand", "other_red_seats"}.isdisjoint(end)
                )
                self.assertTrue(all("P1: I intend" not in e["text"] for e in end["new_history"]))
