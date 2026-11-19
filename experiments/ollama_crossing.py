"""Two-turn integration trial. Only seat P2 queries the installed model."""

import argparse
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from random import Random

from footsteps.ollama import Seat, ServiceError, infer, play_seat
from footsteps.record import read, replay
from footsteps.table import Table
from footsteps.table_server import TableServer

CROSSING = Path(__file__).resolve().parents[1] / "examples/crossing.json"


def scripted(seat):
    snapshot = seat.call("/ready", {})
    while snapshot["phase"] != "over":
        if snapshot["choices"]:
            state = snapshot["state"]
            stage = state["stage"]
            player = snapshot["seat"]
            if stage == "place":
                choice = (
                    {"tile": 40, "at": [1, 0], "rotation": 0}
                    if player == 0
                    else {"tile": 9, "at": [0, 1], "rotation": 1}
                )
            elif stage == "discard":
                choice = {"tile": 18}
            elif stage == "propose":
                choice = {"to": [state["turn"], 0]}
            elif stage == "nominate":
                choice = {"target": 3 if player == 1 and 3 in state["alive"] else None}
            else:
                choice = {"vote": player != 3 and (stage == "move_vote" or state["pending"] == 3)}
            try:
                seat.call("/choice", {"revision": snapshot["revision"], "choice": choice})
            except ServiceError as e:
                if e.status != 409:
                    raise
        time.sleep(0.1)
        snapshot = seat.call("/state")


def trial(path, model):
    table = Table(read(CROSSING)["setup"], Random(1), seconds=30, discussion=0)
    with TableServer(table, path) as host:
        seats = {
            p: Seat(f"http://127.0.0.1:{host.server_port}/#{token}")
            for token, p in host.tokens.items()
        }
        serving = threading.Thread(target=host.serve_forever, kwargs={"poll_interval": 0.1})
        serving.start()

        def hold_first_reply(snapshot, model, seconds):
            start = time.monotonic()
            choice = infer(snapshot, model, seconds)
            elapsed = time.monotonic() - start
            print(f"Event {snapshot['revision']} inference took {elapsed:.2f}s", flush=True)
            if snapshot["revision"] == 4:
                time.sleep(max(0, seconds - elapsed + 0.5))
            return choice

        try:
            with ThreadPoolExecutor(3) as pool:
                other = [pool.submit(scripted, seats[i]) for i in (0, 1, 3)]
                play_seat(seats[2], model, 30, decide=hold_first_reply)
                for task in other:
                    task.result()
        finally:
            host.shutdown()
            serving.join()
    record = read(path)
    votes = [e["votes"] for e in record["events"] if e["kind"] == "move_vote"]
    print(f"{replay(record).winner} team wins. Movement ballots: {votes}")
    if len(votes) != 2 or votes[0][2] is not None or votes[1][2] is None:
        raise RuntimeError("trial did not capture both a missed and a completed movement ballot")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default="qwen2.5:3b")
    parser.add_argument("--save", required=True, type=Path)
    args = parser.parse_args()
    trial(args.save, args.model)
