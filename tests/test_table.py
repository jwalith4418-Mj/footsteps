import json
import tempfile
import threading
import time
import unittest
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from random import Random
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from footsteps.ollama import Seat, ServiceError
from footsteps.record import read, replay
from footsteps.table import PAPER_KIT, DecisionConflict, Table, fixed_kit, paper_setup
from footsteps.table_server import TableServer

CROSSING = read(Path(__file__).resolve().parents[1] / "examples/crossing.json")


class LiveDecisions(unittest.TestCase):
    def test_uniform_kit_counts_cover_separate_slots_and_survive_the_deal(self):
        for seed in range(8):
            low = fixed_kit(Random(seed), 16, 29, 29)
            high = fixed_kit(Random(seed), 16, 35, 35)
            self.assertTrue(all(a & b == a for a, b in zip(low, high, strict=True)))
            for tiles, count in ((low, 29), (high, 35)):
                self.assertEqual(sum((t & 15).bit_count() for t in tiles), count)
                self.assertEqual(sum((t >> 4).bit_count() for t in tiles), count)
                self.assertEqual(tiles, fixed_kit(Random(seed), 16, count, count))
                self.assertNotEqual([t & 15 for t in tiles], [t >> 4 for t in tiles])
                setup = paper_setup(Random(seed), kit=tiles)
                self.assertCountEqual(sum(setup["hands"], setup["store"].copy()), tiles)
        self.assertEqual(fixed_kit(Random(2), 2, 0, 8), (240, 240))
        self.assertEqual(fixed_kit(Random(2), 2, 8, 0), (15, 15))
        for counts in ((-1, 0), (0, 9)):
            with self.assertRaises(ValueError):
                fixed_kit(Random(1), 2, *counts)

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

    def test_three_seat_paper_deal_finishes_through_all_deadlines(self):
        setup = paper_setup(Random(13), 3)
        self.assertEqual(sorted(setup["roles"]), ["blue", "blue", "red"])
        self.assertEqual(list(map(len, setup["hands"])), [2, 2, 2])
        self.assertEqual(len(setup["store"]), 10)
        self.assertEqual(Counter(sum(setup["hands"], setup["store"])), Counter(PAPER_KIT))
        table = Table(setup, Random(1), seconds=1, discussion=0)
        for seat in range(3):
            table.join(seat, 0)
        for tick in range(1, 100):
            table.tick(tick)
        final = replay(table.record)
        self.assertEqual((final.winner, final.turn), ("red", 10))

    def test_all_timeouts_terminate_and_replay(self):
        table = Table(paper_setup(Random(4)), Random(5), seconds=1, discussion=0)
        for seat in range(4):
            table.join(seat, 0)
        for tick in range(1, 100):
            table.tick(tick)
        game = replay(table.record)
        self.assertEqual((game.winner, game.turn), ("red", 8))
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

    def test_committed_placement_owns_the_callers_coordinate_list(self):
        table = Table(CROSSING["setup"], Random(1))
        for seat in range(4):
            table.join(seat, 0)
        square = [1, 0]
        table.submit(0, 1, {"tile": 40, "rotation": 0, "at": square}, 0)
        square[:] = [0, 1]
        self.assertEqual(table.game.placements, {(1, 0): (40, 0)})
        self.assertEqual(replay(table.record).placements, {(1, 0): (40, 0)})

    def test_committed_draw_owns_the_drawn_list(self):
        class CapturingRandom(Random):
            def __init__(self, seed):
                super().__init__(seed)
                self.draws = []

            def sample(self, population, k):
                draw = super().sample(population, k)
                self.draws.append(draw)
                return draw

        rng = CapturingRandom(1)
        table = Table(CROSSING["setup"], rng)
        for seat in range(4):
            table.join(seat, 0)
        self.assertEqual(table.record["events"][0]["kind"], "draw")
        recorded = list(table.record["events"][0]["tiles"])
        rng.draws[0][:] = [0, 0]
        self.assertEqual(table.record["events"][0]["tiles"], recorded)
        self.assertEqual(replay(table.record).hands[0], table.game.hands[0])


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

    def test_private_orient_endpoint_and_reconnected_commit(self):
        for seat in range(4):
            self.api(seat, "/ready")
        other = self.api(1)
        for _ in range(2):
            snap = self.api(0, "/orient", revision=1, piece="H1", rotation=2)
            self.assertEqual(snap["pieces"]["H1"], [40, 2])
            self.assertEqual(snap["revision"], 1)
        self.assertEqual(self.api(1), other)
        self.assertEqual(self.api(0)["pieces"], snap["pieces"])
        self.api(
            0,
            "/choice",
            revision=1,
            choice={"piece": "H1", "at": [1, 0], "expected_orientation": 2},
        )
        self.assertEqual(
            read(self.path)["events"][-1],
            {"kind": "place", "tile": 40, "at": [1, 0], "rotation": 2},
        )
        with self.assertRaises(HTTPError) as stale:
            self.api(0, "/orient", revision=1, piece="H1", rotation=0)
        self.assertEqual(stale.exception.code, 409)

    def test_note_identity_persisted_only_when_requested(self):
        self.assertNotIn("table_id", read(self.path))
        first = self.api(0, "/ready", request_note_id=True)
        self.assertEqual(first["table_id"], read(self.path)["table_id"])
        self.assertNotIn("table_id", self.api(1, "/ready"))
        self.assertEqual(self.api(2, "/ready", request_note_id=True)["table_id"], first["table_id"])
        self.assertEqual(self.api(0, "/state")["table_id"], first["table_id"])
        self.assertNotIn("table_id", self.api(1, "/state"))

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
        self.assertEqual(replay(read(self.path)).winner, "blue")
        self.assertEqual(self.api(3)["state"]["roles"], CROSSING["setup"]["roles"])
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)

    def test_browser_assets_and_unknown_route(self):
        root = f"http://127.0.0.1:{self.server.server_port}"
        for path, mime, content in (
            ("/", "text/html", b"/table.js"),
            ("/table.js", "text/javascript", b"function render"),
            ("/table.css", "text/css", b".face"),
        ):
            with self.subTest(path=path), urlopen(root + path, timeout=3) as response:
                self.assertEqual(response.headers.get_content_type(), mime)
                self.assertIn(content, response.read())
        for request in (Request(root + "/missing"), Request(root + "/missing", data=b"{}")):
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=3)
            self.assertEqual(error.exception.code, 404)

    def test_model_seat_transport_and_discussion_checkpoint(self):
        base = f"http://127.0.0.1:{self.server.server_port}/#"
        seats = [Seat(base + self.tokens[i]) for i in range(4)]
        self.table.discussion = 5
        for i, seat in enumerate(seats):
            self.assertEqual(seat.call("/ready", {})["seat"], i)
        with self.assertRaises(ServiceError) as illegal:
            seats[0].call("/choice", {"revision": 1, "choice": {}})
        self.assertEqual(illegal.exception.status, 400)
        self.assertEqual(seats[0].call("/state")["revision"], 1)
        for rev, event in enumerate(CROSSING["events"][1:4], start=1):
            choice = {k: v for k, v in event.items() if k != "kind"}
            seats[0].call("/choice", {"revision": rev, "choice": choice})
        seats[1].call("/say", {"revision": 4, "text": "  Face 40 leads east.  "})
        saved = read(self.path)
        self.assertEqual(
            saved["remarks"], [{"after_event": 4, "seat": 1, "text": "Face 40 leads east."}]
        )
        self.assertEqual(replay(saved).stage, "move_vote")
        self.assertEqual(seats[2].call("/state")["history"][-1]["text"], "P1: Face 40 leads east.")
        with self.assertRaises(ServiceError) as repeated:
            seats[1].call("/say", {"revision": 4, "text": "another remark"})
        self.assertEqual(repeated.exception.status, 409)
        self.assertEqual(read(self.path), saved)

    def test_existing_record_is_preserved(self):
        with self.assertRaises(FileExistsError):
            TableServer(self.table, self.path)
        self.assertEqual(read(self.path), self.table.record)
