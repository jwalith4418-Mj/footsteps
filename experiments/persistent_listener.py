"""One persistent Blue P3 at a real localhost table with three scripted opponents."""

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from random import Random

from footsteps.decision_notes import open_private
from footsteps.ollama import Seat, request
from footsteps.record import read, replay, starting_game
from footsteps.session import Session
from footsteps.table import Table
from footsteps.table_server import TableServer


def opponents(server, done, p0_yes):
    """Script non-focal seats using their legal choices and the referee clock."""
    t = server.table
    while not done.wait(0.05):
        with server.lock:
            now = server.clock()
            t.tick(now)
            if t.game.winner:
                return
            for i in (0, 1, 2):
                s = t.view(i, now)
                g = s["state"]
                if (
                    g["stage"] == "eliminate_vote"
                    and g["pending"] == 0
                    and i == 2
                    and t.speaking(i, now)
                ):
                    t.say(
                        i,
                        t.revision,
                        "P0 voted No on the first marker step. We should remove P0.",
                        now,
                    )
                if not s["choices"]:
                    continue
                c = s["choices"]
                if g["stage"] == "place":
                    choice = {
                        "tile": 40 if g["turn"] == 1 else c["tile"][0],
                        "at": [1, 0] if g["turn"] == 1 else [0, 1],
                        "rotation": 0,
                    }
                elif g["stage"] == "discard":
                    choice = {"tile": c["tile"][0]}
                elif g["stage"] == "propose":
                    choice = {"to": [1, 0] if g["turn"] == 1 else [2, 0]}
                elif g["stage"] == "nominate":
                    choice = {"target": 0 if i == 1 and g["turn"] == 1 else None}
                else:
                    vote = g["stage"] == "move_vote"
                    if vote and g["turn"] == 1 and i == 0:
                        vote = p0_yes
                    choice = {"vote": vote}
                t.submit(i, t.revision, choice, now)
            server.save()


def trial(root, private, model, p0_yes=True):
    root.mkdir(exist_ok=False)
    setup = read(Path(__file__).resolve().parents[1] / "examples/crossing.json")["setup"]
    setup["roles"] = ["blue", "blue", "red", "blue"]
    table = Table(setup, Random(1), seconds=30, discussion=15)
    request(
        11434,
        "/api/chat",
        {
            "model": model,
            "messages": [],
            "stream": False,
            "options": {"num_ctx": 8192},
            "keep_alive": "10m",
        },
        120,
    )
    with open_private(private) as trace, TableServer(table, root / "game.json") as host:
        seats = {
            i: Seat(f"http://127.0.0.1:{host.server_port}/#{token}")
            for token, i in host.tokens.items()
        }
        serving = threading.Thread(target=host.serve_forever, kwargs={"poll_interval": 0.05})
        serving.start()
        done = threading.Event()

        try:
            for seat in seats.values():
                seat.call("/ready", {})
            session = Session(seats[3])
            forced = False
            with ThreadPoolExecutor(1) as pool, (root / "calls.jsonl").open("x") as log:
                script = pool.submit(opponents, host, done, p0_yes)
                try:
                    while True:
                        if script.done():
                            script.result()
                        session.refresh()
                        if session.snap["phase"] == "over":
                            break
                        force = not forced and any(
                            e["kind"] == "eliminate_vote" for e in session.snap["history"]
                        )
                        row = session.step(model, force_compact=force)
                        if row is None:
                            continue
                        if force and row["result"].get("compacted"):
                            forced = True
                        print(json.dumps(row), file=trace, flush=True)
                        public = {
                            k: row[k]
                            for k in (
                                "revision",
                                "tool",
                                "prompt_tokens",
                                "reply_tokens",
                                "inference_seconds",
                            )
                        }
                        public.update(
                            model=model, forced_compaction=force, error="error" in row["result"]
                        )
                        if row["tool"] == "history":
                            public.update(
                                filters=row["arguments"],
                                entry_ids=[e["id"] for e in row["result"].get("entries", [])],
                            )
                        print(json.dumps(public), file=log, flush=True)
                finally:
                    done.set()
                script.result()
        finally:
            done.set()
            host.shutdown()
            serving.join()
            with host.lock:
                host.save()
    game = replay(read(root / "game.json"))
    print(game.winner, "won on turn", game.turn)


def report(root):
    record = read(root / "game.json")
    game = starting_game(record)
    decisions = []
    for i, event in enumerate(record["events"], 1):
        if event["kind"] in ("move_vote", "eliminate_vote") and 3 in game.alive:
            vote = event["votes"][game.alive.index(3)]
            decisions.append((i, event["kind"], vote, "missed" if vote is None else "cast"))
        if event["kind"] == "nominate" and game.queue[0] == 3:
            decisions.append(
                (i, "nominate", event["target"], "missed" if event.get("timeout") else "cast")
            )
        game.apply(event)
    assert game.winner
    calls = [json.loads(line) for line in (root / "calls.jsonl").read_text().splitlines()]
    print("P3 decisions", decisions)
    print(
        "Requests",
        len(calls),
        "prompt tokens",
        sum(r["prompt_tokens"] for r in calls),
        "generated tokens",
        sum(r["reply_tokens"] for r in calls),
        "inference seconds",
        round(sum(r["inference_seconds"] for r in calls), 1),
    )
    print("History queries", [r for r in calls if r["tool"] == "history"])
    print(
        "Compactions",
        [
            (r["revision"], r["forced_compaction"], r["error"])
            for r in calls
            if r["tool"] == "compact"
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument(
        "private", type=Path, nargs="?", help="new private trace; omit to audit saved outputs"
    )
    parser.add_argument("--model", default="footsteps-qwen3.8:27b-rana-layout")
    parser.add_argument("--true-claim", action="store_true", help="P0 votes No on the first move")
    args = parser.parse_args()
    if args.private:
        trial(args.root, args.private, args.model, not args.true_claim)
    report(args.root)
