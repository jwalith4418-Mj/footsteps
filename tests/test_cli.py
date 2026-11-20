"""Exercise the command line in-process so coverage follows the same entry point as python -m."""

import io
import json
import os
import runpy
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from random import Random
from unittest.mock import patch

from footsteps.record import read, replay
from footsteps.table import Table

EXAMPLE = Path(__file__).resolve().parents[1] / "examples/crossing.json"


def invoke(*args, stdin=""):
    out, err = io.StringIO(), io.StringIO()
    argv = ["footsteps", *map(str, args)]
    with (
        patch.object(sys, "argv", argv),
        patch.object(sys, "stdin", io.StringIO(stdin)),
        redirect_stdout(out),
        redirect_stderr(err),
    ):
        try:
            runpy.run_module("footsteps", run_name="__main__")
            code = 0
        except SystemExit as e:
            code = e.code
    return code, out.getvalue(), err.getvalue()


class Commands(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(self.enterContext(tempfile.TemporaryDirectory()))

    def ok(self, *args, **kwargs):
        code, out, err = invoke(*args, **kwargs)
        self.assertEqual(code, 0, err)
        return out

    def test_human_game_from_menus_to_replay(self):
        path = self.tmp / "game.json"
        # Two open tiles in the bag. Rotate the first and bridge east, then move into EXIT.
        answers = ["oops", "0", "1", "2", "4", "1", "2", "1", "1", "1", "2"]
        output = self.ok(
            "solo",
            "--policy",
            "human",
            "--goal",
            2,
            0,
            "--hand",
            0,
            "--store",
            2,
            "--density",
            1,
            "--save",
            path,
            stdin="\n".join(answers),
        )
        self.assertEqual(output.count("Enter a number from 1 through 2."), 2)
        self.assertIn("90° · in NESW, out NESW", output)
        self.assertEqual(output.count("Return to store"), 1)
        r = read(path)
        self.assertEqual(
            r["events"][1], {"kind": "place", "tile": 255, "rotation": 1, "at": [1, 0]}
        )
        self.assertEqual([e["votes"] for e in r["events"] if "votes" in e], [[True], [True]])
        self.assertEqual(replay(r).winner, "good")
        self.assertTrue(output.endswith(self.ok("replay", path)))

    def test_human_stays_and_store_runs_out(self):
        path = self.tmp / "closed.json"
        output = self.ok(
            "solo",
            "--policy",
            "human",
            "--hand",
            0,
            "--store",
            1,
            "--density",
            0,
            "--save",
            path,
            stdin="1\n1\n1\n1\n",
        )
        self.assertIn("in –, out –", output)
        self.assertIn("Winner: **bad**", output)
        self.assertEqual(read(path)["events"][-1], {"kind": "propose", "to": None})

    def test_policy_game_account_import_and_view(self):
        path = self.tmp / "solo.json"
        output = self.ok("solo", "--seed", 59, "--goal", 6, 0, "--policy", "route", "--save", path)
        self.assertEqual(self.ok("replay", path), output)
        full = self.tmp / "full.md"
        full.write_text(self.ok("replay", path, "--full"))
        self.assertEqual(read(full), read(path))
        html = self.tmp / "game.html"
        for flags in [(), ("--seat", "0"), ("--omniscient",)]:
            with self.subTest(flags=flags):
                self.ok("view", full, *flags, "-o", html)
                payload = (
                    html.read_text().split('type="application/json">')[1].split("</script>")[0]
                )
                first = json.loads(payload)["frames"][0]
                self.assertEqual("hand" in first, "--seat" in flags)
                self.assertEqual("hands" in first, "--omniscient" in flags)

    def test_model_cli_encodes_and_submits_a_named_move(self):
        record = read(EXAMPLE)
        table = Table(record["setup"], Random(1), discussion=0)
        for seat in range(4):
            table.join(seat, 0)
        for event in record["events"][1:3]:
            table.submit(0, table.revision, {k: v for k, v in event.items() if k != "kind"}, 0)
        snapshot = json.loads(json.dumps(table.view(0, 0)))

        def transport(port, path, body, timeout, token=None):
            if path == "/ready":
                self.assertEqual((port, token, body), (9090, "seat0", {}))
                return snapshot
            if path == "/api/chat":
                self.assertEqual((port, token, body["model"]), (11434, None, "test-model"))
                self.assertIs(body["think"], False)
                self.assertIn("Good: build", body["messages"][0]["content"])
                self.assertEqual(body["format"]["properties"]["to"]["enum"], ["stay", "east"])
                self.assertLessEqual(timeout, 4)
                return {"message": {"content": '{"to":"east"}'}}
            self.assertEqual((port, path, token), (9090, "/choice", "seat0"))
            self.assertEqual(body, {"revision": 3, "choice": {"to": [1, 0]}})
            return {"phase": "over", "state": {"winner": "good"}}

        with (
            patch("getpass.getpass", return_value="http://127.0.0.1:9090/#seat0"),
            patch("footsteps.ollama.request", side_effect=transport),
        ):
            output = self.ok(
                "ollama",
                "--model",
                "test-model",
                "--named-moves",
                "--no-think",
                "--guided",
                "--budget",
                4,
            )
        self.assertIn("Good team wins.", output)

    def test_output_alias_leaves_input_readable(self):
        path = self.tmp / "game.json"
        path.write_bytes(EXAMPLE.read_bytes())
        alias = self.tmp / "also-game.json"
        os.link(path, alias)
        for dest in (alias, path):
            code, _, err = invoke("view", path, "-o", dest)
            self.assertEqual(code, 2)
            self.assertIn("separate from the input", err)
            self.assertEqual(path.read_bytes(), EXAMPLE.read_bytes())

    def test_invalid_invocations_do_not_create_output(self):
        path = self.tmp / "save"
        cases = [
            (("table", "--kit-counts", "65", "0", "--save", path), "0..64"),
            (("table", "--kit-seed", "1", "--save", path), "--kit-counts"),
            (("table", "--port", "65536", "--save", path), "port"),
            (("table", "--crossing", "--seats", "3", "--save", path), "four seats"),
            (("solo", "--store", "0", "--save", path), "store >= 1"),
            (("replay", EXAMPLE, "--seat", "-1"), "invalid seat"),
            (("view", EXAMPLE, "--seat", "0", "--omniscient", "-o", path), "not allowed"),
        ]
        for args, reason in cases:
            with self.subTest(args=args):
                code, _, err = invoke(*args)
                self.assertEqual(code, 2)
                self.assertIn(reason, err)
                self.assertFalse(path.exists())
        code, _, err = invoke("solo", "--policy", "human", "--save", path, stdin="")
        self.assertEqual(code, 1)
        self.assertIn("interrupted", err)
        self.assertFalse(path.exists())

    def test_host_checkpoints_both_deals_at_launch_and_shutdown(self):
        for flags, seats in [
            (("--crossing",), 4),
            (("--seats", "3"), 3),
            (("--kit-counts", "29", "29", "--kit-seed", "8700"), 4),
        ]:
            path = self.tmp / f"host-{flags[0]}.json"
            with (
                self.subTest(flags=flags),
                patch(
                    "footsteps.table_server.TableServer.serve_forever",
                    side_effect=KeyboardInterrupt,
                ),
            ):
                output = self.ok("table", "--save", path, *flags)
                self.assertEqual(output.count("http://127.0.0.1:"), seats)
                record = read(path)
                self.assertEqual(len(record["setup"]["roles"]), seats)
                self.assertEqual(replay(record).stage, "draw")
                if "--kit-counts" in flags:
                    tiles = sum(record["setup"]["hands"], record["setup"]["store"].copy())
                    self.assertEqual(sum((t & 15).bit_count() for t in tiles), 29)
                    self.assertEqual(sum((t >> 4).bit_count() for t in tiles), 29)
                if "--crossing" in flags:
                    self.assertEqual(record["setup"], read(EXAMPLE)["setup"])
