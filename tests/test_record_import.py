"""The full Markdown account imports its final labeled block, not an earlier example."""

import json
import unittest
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory

from footsteps.record import FENCE, read, render, replay
from footsteps.viewer import transcript

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/crossing.json"


class FullAccountImport(unittest.TestCase):
    def write(self, text):
        tmp = TemporaryDirectory()
        path = Path(tmp.name) / "worked.md"
        path.write_text(text)
        self.addCleanup(tmp.cleanup)
        return path

    def test_plain_json_still_imports(self):
        self.assertEqual(read(EXAMPLE)["format"], 3)
        replay(read(EXAMPLE))

    def test_old_wire_ids_upgrade_once_and_keep_speech_and_seat_visibility(self):
        archived = json.loads((Path(__file__).parent / "fixtures/crossing-v1.json").read_text())
        for version in (1, 2):
            raw = deepcopy(archived)
            raw["format"] = version
            raw["setup"]["start"] = [7, 9] if version == 1 else [0, 0]
            raw["table_id"] = "fixture"
            # The speaker may use the exact spellings of historical wire IDs.
            speech = "My team's name was " + raw["setup"]["roles"][3]
            raw["remarks"] = [{"after_event": 4, "seat": 3, "text": speech}]
            original = deepcopy(raw)
            imported = read(self.write(render(raw, full=True)))
            self.assertEqual(raw, original)
            self.assertEqual(imported["format"], 3)
            self.assertEqual(imported["setup"], read(EXAMPLE)["setup"])
            for field in ("table_id", "events", "remarks"):
                self.assertEqual(imported[field], raw[field])
            self.assertEqual(replay(imported).winner, "blue")
            public = transcript(imported)["frames"]
            self.assertNotIn("roles", public[0])
            self.assertEqual(public[4]["remarks"][0]["text"], speech)
            self.assertEqual(transcript(imported, 3)["frames"][0]["role"], "red")
            self.assertNotIn("teammates", transcript(imported, 0)["frames"][0])
        invalid = {**imported, "setup": {**imported["setup"], "roles": archived["setup"]["roles"]}}
        with self.assertRaisesRegex(ValueError, "invalid teams"):
            replay(invalid)

    def test_full_markdown_round_trip(self):
        record = read(EXAMPLE)
        path = self.write(render(record, full=True))
        self.assertEqual(read(path), record)
        replay(read(path))
        transcript(read(path))

    def test_earlier_example_does_not_shadow_final_block(self):
        record = read(EXAMPLE)
        intro = "An example of the block syntax:\n" + FENCE + "{}\n```\n\n"
        path = self.write(intro + render(record, full=True))
        self.assertEqual(read(path), record)
        replay(read(path))
        transcript(read(path))

    def test_truncated_final_block_is_rejected(self):
        record = read(EXAMPLE)
        full = render(record, full=True)
        with self.assertRaises(ValueError):
            read(self.write(full[: full.rindex("\n```")]))
        intro = "An example:\n" + FENCE + "{}\n```\n\n"
        with self.assertRaises(ValueError):
            read(self.write(intro + full[: full.rindex("\n```")]))

    def test_trailing_non_whitespace_is_rejected(self):
        record = read(EXAMPLE)
        with self.assertRaises(ValueError):
            read(self.write(render(record, full=True) + "After the block.\n"))

    def test_invalid_final_block_after_valid_example(self):
        record = read(EXAMPLE)
        earlier = "Example:\n" + FENCE + json.dumps(record, indent=2) + "\n```\n\n"
        # A final block that is not JSON must not fall back to the earlier example.
        with self.assertRaises(ValueError):
            read(self.write(earlier + "Final:\n" + FENCE + "{ not json\n```\n"))
        # A final block that is JSON but not a valid record must fail replay.
        with self.assertRaises(ValueError):
            replay(read(self.write(earlier + "Final:\n" + FENCE + '{"format": 99}\n```\n')))


if __name__ == "__main__":
    unittest.main()
