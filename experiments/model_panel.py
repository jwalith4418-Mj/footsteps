"""Play one three- or four-seat game through the live API, recording every model call's latency."""

import argparse
import csv
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from http.client import HTTPException
from pathlib import Path
from random import Random

from footsteps.ollama import Seat, infer, play_seat, request
from footsteps.record import read, replay
from footsteps.table import Table, paper_setup
from footsteps.table_server import TableServer


def run(models, guided, seed, output, named_moves=False, no_think=False, seats=4):
    if len(models) == 1:
        models = models * seats
    if len(models) != seats:
        raise ValueError("supply one shared model or a model for each seat")
    output.mkdir(parents=True, exist_ok=False)
    path = output / "game.json"
    table = Table(
        paper_setup(Random(seed), seats), Random(f"draw/{seed}"), seconds=15, discussion=0
    )
    epoch = time.monotonic()
    with TableServer(table, path) as host:
        server = threading.Thread(target=host.serve_forever, kwargs={"poll_interval": 0.05})
        server.start()

        def player(token):
            client = Seat(f"http://127.0.0.1:{host.server_port}/#{token}")
            model = models[host.tokens[token]]
            rows = []

            def timed(snapshot, name, seconds):
                start = time.monotonic()
                row = {
                    "event": snapshot["revision"] + 1,
                    "seat": snapshot["seat"],
                    "stage": snapshot["state"]["stage"],
                    "choice": "",
                    "error": "",
                    "model": name,
                    "remaining_ms": round(1000 * snapshot["seconds_left"]),
                    "start_ms": round(1000 * (start - epoch)),
                }
                try:
                    choice = infer(
                        snapshot,
                        name,
                        seconds,
                        guided=guided,
                        named_moves=named_moves,
                        no_think=no_think,
                    )
                    row["choice"] = json.dumps(choice, separators=(",", ":"))
                    return choice
                except (OSError, HTTPException, ValueError, TypeError, KeyError) as exc:
                    row["error"] = f"{type(exc).__name__}: {exc}"
                    raise
                finally:
                    row["ms"] = round(1000 * (time.monotonic() - start))
                    rows.append(row)

            play_seat(client, model, 15, decide=timed, report=lambda _: None)
            return rows

        try:
            residency = []
            with ThreadPoolExecutor(seats) as pool:
                workers = [pool.submit(player, token) for token in host.tokens]
                if len(set(models)) > 1:
                    while True:
                        loaded = request(11434, "/api/ps", None, 3)["models"]
                        residency.append(
                            {
                                "ms": round(1000 * (time.monotonic() - epoch)),
                                "models": [
                                    {k: m[k] for k in ("name", "size", "size_vram")}
                                    for m in loaded
                                    if m["name"] in models
                                ],
                            }
                        )
                        if not wait(workers, timeout=0.5).not_done:
                            break
                rows = [row for worker in workers for row in worker.result()]
        finally:
            host.shutdown()
            server.join()
    if residency:
        (output / "residency.json").write_text(json.dumps(residency) + "\n")
    record = read(path)
    game = replay(record)
    if not game.winner:
        raise ValueError("game did not finish")
    with (output / "calls.csv").open("x", newline="") as f:
        writer = csv.DictWriter(
            f,
            lineterminator="\n",
            fieldnames=[
                "event",
                "seat",
                "stage",
                "ms",
                "choice",
                "error",
                "model",
                "start_ms",
                "remaining_ms",
            ],
        )
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["event"], r["seat"])))
    print(
        f"{models} guided={guided} seed={seed} {game.winner} on turn {game.turn}; {len(rows)} calls",
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", required=True, nargs="+", help="one shared tag or one tag per seat, in order"
    )
    parser.add_argument("--guided", action="store_true")
    parser.add_argument("--seed", required=True, type=int)
    parser.add_argument("--out", required=True, type=Path, help="new game directory")
    parser.add_argument("--named-moves", action="store_true")
    parser.add_argument("--no-think", action="store_true")
    parser.add_argument("--seats", type=int, choices=(3, 4), default=4)
    args = parser.parse_args()
    run(args.model, args.guided, args.seed, args.out, args.named_moves, args.no_think, args.seats)
