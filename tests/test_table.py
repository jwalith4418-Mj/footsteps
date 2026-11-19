import json
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from random import Random
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from footsteps.record import read, replay
from footsteps.table import DecisionConflict, Table, paper_setup
from footsteps.table_server import TableServer

CROSSING = read(Path(__file__).resolve().parents[1] / "examples/crossing.json")


class LiveDecisions(unittest.TestCase):
    def test_discussion_and_sealed_ballots(self):
        table = Table(CROSSING["setup"], Random(1), seconds=20, discussion=5)
        for seat in range(4):
            table.join(seat, 0)
        for event in CROSSING["events"][1:4]:
            table.submit(0, table.revision, {k: v for k, v in event.items() if k != "kind"}, 1)
        self.assertEqual(table.view(1, 1)["phase"], "discussion")
        with self.assertRaises(DecisionConflict):
            table.submit(0, 4, {"vote": True}, 5)
        table.say(1, 4, "Face 40 admits entry from the west.", 3)
        self.assertTrue(
            all("P1: Face" in table.view(i, 3)["history"][-1]["text"] for i in range(4))
        )
        with self.assertRaises(DecisionConflict):
            table.say(1, 4, "second remark", 4)
        with self.assertRaises(DecisionConflict):
            table.say(2, 4, "too late", 6)
        before = table.view(2, 6)
        table.submit(0, 4, {"vote": True}, 6)
        self.assertEqual(table.view(2, 6), before)
        self.assertTrue(table.view(0, 6)["voted"])
        with self.assertRaises(DecisionConflict):
            table.submit(0, 4, {"vote": False}, 8)
        table.submit(1, 4, {"vote": True}, 8)
        table.submit(3, 4, {"vote": False}, 8)
        with self.assertRaises(DecisionConflict):
            table.submit(2, 4, {"vote": True}, 26)
        self.assertEqual(table.record["events"][-1], CROSSING["events"][4])
        self.assertEqual(table.view(2, 26)["state"]["marker"], (1, 0))
        self.assertEqual(table.record["remarks"][0]["after_event"], 4)

    def test_all_timeouts_terminate_and_replay(self):
        table = Table(paper_setup(Random(4)), Random(5), seconds=1, discussion=0)
        for seat in range(4):
            table.join(seat, 0)
        for tick in range(1, 100):
            table.tick(tick)
        game = replay(table.record)
        self.assertEqual((game.winner, game.turn), ("bad", 8))
        self.assertTrue(any(e["kind"] == "place" and e["timeout"] for e in table.record["events"]))
        self.assertIn("random choice after timeout", str(table.view(1, 101)["history"]))

    def test_invalid_placement_and_stale_resubmission(self):
        table = Table(CROSSING["setup"], Random(1))
        for seat in range(4):
            table.join(seat, 0)
        choice = {"tile": 40, "rotation": 0, "at": [1, 0]}
        with self.assertRaises(DecisionConflict):
            table.submit(1, 1, choice, 1)
        with self.assertRaises(ValueError):
            table.submit(0, 1, {**choice, "timeout": True}, 1)
        with self.assertRaises(ValueError):
            table.submit(0, 1, {**choice, "at": [3, 0]}, 1)
        self.assertEqual(table.revision, 1)
        table.submit(0, 1, choice, 1)
        with self.assertRaises(DecisionConflict):
            table.submit(0, 1, choice, 2)


class LoopbackTable(unittest.TestCase):
    def setUp(self):
        folder = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(folder) / "host.json"
        self.now = 0
        self.table = Table(CROSSING["setup"], Random(1), seconds=10, discussion=0)
        self.server = self.enterContext(TableServer(self.table, self.path, clock=lambda: self.now))
        worker = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.02})
        worker.start()
        self.addCleanup(worker.join)
        self.addCleanup(self.server.shutdown)
        self.tokens = {s: t for t, s in self.server.tokens.items()}

    def api(self, seat, path="/state", **body):
        headers = {} if seat is None else {"Authorization": "Bearer " + self.tokens[seat]}
        payload = None if path == "/state" else json.dumps(body).encode()
        req = Request(f"http://127.0.0.1:{self.server.server_port}{path}", payload, headers)
        with urlopen(req, timeout=3) as response:
            return json.load(response)

    def test_crossing_through_four_private_clients(self):
        for seat in range(4):
            v = self.api(seat, "/ready")
            self.assertEqual(v["seat"], seat)
            self.assertEqual(v["state"]["hand"], CROSSING["setup"]["hands"][seat])
            self.assertNotIn("roles", v["state"])
        self.assertNotIn("18", self.api(1)["history"][0]["text"])
        self.assertEqual(self.api(0)["state"]["hand"], [40, 18, 12])
        with self.assertRaises(HTTPError) as denied:
            self.api(None)
        self.assertEqual(denied.exception.code, 401)
        with self.assertRaises(HTTPError) as wrong:
            self.api(1, "/choice", revision=1, choice={"tile": 40, "at": [1, 0], "rotation": 0})
        self.assertEqual(wrong.exception.code, 409)
        for rev, event in enumerate(CROSSING["events"]):
            kind = event["kind"]
            if kind == "draw":
                continue
            state = self.api(0)["state"]
            args = {k: v for k, v in event.items() if k != "kind"}
            if "votes" in args:
                votes = args["votes"]

                def ballot(pair, revision=rev):
                    seat, value = pair
                    if value is not None:
                        self.api(seat, "/choice", revision=revision, choice={"vote": value})

                with ThreadPoolExecutor(4) as pool:
                    list(pool.map(ballot, zip(state["alive"], votes)))
                if None in votes:
                    self.now += 10
                    # Checkpoint must advance on the server timer with no player polling.
                    limit = time.monotonic() + 2
                    while len(read(self.path)["events"]) == rev and time.monotonic() < limit:
                        time.sleep(0.01)
                    self.assertEqual(len(read(self.path)["events"]), rev + 1)
            else:
                seat = state["nominator"] if kind == "nominate" else state["actor"]
                self.api(seat, "/choice", revision=rev, choice=args)
            if kind == "eliminate_vote":
                spectator = self.api(3)
                self.assertIsNone(spectator["choices"])
                self.assertNotIn("roles", self.api(1)["state"])
        self.assertEqual(read(self.path), CROSSING)
        self.assertEqual(replay(read(self.path)).winner, "good")
        self.assertEqual(self.api(3)["state"]["roles"], CROSSING["setup"]["roles"])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_existing_record_is_preserved(self):
        with self.assertRaises(FileExistsError):
            TableServer(self.table, self.path)
        self.assertEqual(read(self.path), self.table.record)
