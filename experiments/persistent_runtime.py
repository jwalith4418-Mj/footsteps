"""Local hosting, request measurements and publishable receipts shared by persistent-seat studies."""

import json
import threading
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from time import monotonic, sleep

from footsteps.decision_notes import open_private
from footsteps.ollama import Seat, ServiceError, request
from footsteps.record import read, replay
from footsteps.session import Session
from footsteps.table_server import TableServer


def play_table(
    root,
    private,
    model,
    table,
    focal,
    *,
    opponents=None,
    compact_when=None,
    session_class=Session,
    context=8192,
):
    """Play and record one authenticated persistent seat under a real referee clock."""
    with (
        open_private(private) as trace,
        live_table(root, table, model, context=context) as (host, seats),
    ):
        done = threading.Event()
        session = session_class(seats[focal], context=context)
        forced = False
        with ThreadPoolExecutor(1) as pool, (root / "calls.jsonl").open("x") as log:
            script = pool.submit(opponents, host, done) if opponents else None
            try:
                while True:
                    if script and script.done():
                        script.result()
                    session.refresh()
                    if session.snap["phase"] == "over":
                        break
                    row = measured_step(
                        session,
                        model,
                        budget=table.seconds,
                        compact_when=None if forced else compact_when,
                    )
                    if row is None:
                        continue
                    force = row.get("forced_compaction", False)
                    if force and (
                        row["result"].get("compacted") or row["result"].get("context_recovered")
                    ):
                        forced = True
                    print(json.dumps(row), file=trace, flush=True)
                    public = public_call(row, model, force)
                    print(json.dumps(public), file=log, flush=True)
            finally:
                done.set()
            if script:
                script.result()
    game = replay(read(root / "game.json"))
    print(game.winner, "won on turn", game.turn)


def resident_model(model):
    for resident in request(11434, "/api/ps", None, 10)["models"]:
        if resident["name"] == model:
            return {
                key: resident.get(key) for key in ("size", "size_vram", "context_length", "digest")
            }
    return None


@contextmanager
def live_table(root, table, model, *, context=8192):
    root.mkdir(exist_ok=False)
    request(
        11434,
        "/api/chat",
        {
            "model": model,
            "messages": [],
            "stream": False,
            "options": {"num_ctx": context},
            "keep_alive": "10m",
        },
        120,
    )
    with TableServer(table, root / "game.json") as host:
        seats = {
            i: Seat(f"http://127.0.0.1:{host.server_port}/#{token}")
            for token, i in host.tokens.items()
        }
        serving = threading.Thread(target=host.serve_forever, kwargs={"poll_interval": 0.05})
        serving.start()

        try:
            for seat in seats.values():
                seat.call("/ready", {})
            yield host, seats
        finally:
            host.shutdown()
            serving.join()
            with host.lock:
                host.save()


def measured_step(session, model, **kwargs):
    revision = session.snap["revision"]
    start = monotonic()
    try:
        return session.step(model, **kwargs)
    except (TimeoutError, ServiceError) as exc:
        if isinstance(exc, ServiceError) and exc.status < 500:
            raise
        error = "request timed out" if isinstance(exc, TimeoutError) else str(exc)
        sleep(0.15)
        # The table's clock continues. Its eventual record determines whether a choice was missed.
        return {
            "revision": revision,
            "tool": None,
            "arguments": {},
            "result": {"error": error},
            "prompt_tokens": None,
            "reply_tokens": None,
            "inference_seconds": round(monotonic() - start, 3),
        }


def public_call(row, model, force):
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
        {
            k: row[k]
            for k in (
                "num_ctx",
                "num_predict",
                "prefill_seconds",
                "generation_seconds",
                "opportunity",
            )
            if k in row
        }
    )
    failed = "error" in row["result"]
    public.update(model=model, forced_compaction=force, error=failed)
    if failed and row["tool"] is not None and not row.get("tool_offered"):
        public["tool"] = "unavailable_tool"
    if row["result"].get("context_recovered"):
        public["context_recovered"] = True
    if "repeat" in row["result"]:
        public["shortened_read"] = True
    elif public["tool"] == "history":
        public.update(
            filters={} if failed else row["arguments"],
            entry_ids=[e["id"] for e in row["result"].get("entries", [])],
        )
    if row["tool"] is None and row["prompt_tokens"] is None:
        public["request_error"] = row["result"]["error"]
    return public
