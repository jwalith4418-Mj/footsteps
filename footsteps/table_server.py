"""Loopback HTTP transport for one referee and its private seat links."""

import json
import os
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from random import Random, SystemRandom
from tempfile import NamedTemporaryFile

from .record import read
from .table import DecisionConflict, Table, fixed_kit, paper_setup

WEB = Path(__file__).with_name("web")
ASSETS = {
    "/": ("table.html", "text/html; charset=utf-8"),
    "/table.js": ("table.js", "text/javascript; charset=utf-8"),
    "/table.css": ("table.css", "text/css; charset=utf-8"),
}


def checkpoint(path, record, *, create=False):
    """Install a complete, owner-readable referee file; reserve a new name on launch."""
    with NamedTemporaryFile(dir=path.parent, delete=False) as f:
        tmp = Path(f.name)
        try:
            f.write((json.dumps(record, indent=2) + "\n").encode())
            f.flush()
            if create:
                os.link(tmp, path)
            else:
                os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)


class TableServer(ThreadingHTTPServer):
    def __init__(self, table, output, port=0, clock=time.monotonic):
        self.table = table
        self.note_seats = set()
        self.output = output
        self.clock = clock
        self.lock = threading.Lock()
        self.tokens = {secrets.token_urlsafe(32): seat for seat in range(len(table.game.roles))}
        super().__init__(("127.0.0.1", port), Handler)
        try:
            checkpoint(output, table.record, create=True)
        except BaseException:
            self.server_close()
            raise
        self.saved = (0, 0, table.record.get("table_id"))

    def save(self):
        stamp = (
            self.table.revision,
            len(self.table.record.get("remarks", ())),
            self.table.record.get("table_id"),
        )
        if stamp != self.saved:
            checkpoint(self.output, self.table.record)
            self.saved = stamp

    def service_actions(self):
        with self.lock:
            self.table.tick(self.clock())
            self.save()


class Handler(BaseHTTPRequestHandler):
    def send(self, code, body, mime="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def error(self, code, text):
        self.send(code, json.dumps({"error": text}).encode())

    def log_message(self, fmt, *args):
        # The referee terminal prints seat links once. It needs no per-poll access log.
        pass

    def do_GET(self):
        if self.path in ASSETS:
            name, mime = ASSETS[self.path]
            self.send(200, (WEB / name).read_bytes(), mime)
        elif self.path == "/state":
            self.api()
        else:
            self.error(404, "Unknown route")

    def do_POST(self):
        if self.path in ("/ready", "/choice", "/say"):
            self.api()
        else:
            self.error(404, "Unknown route")

    def api(self):
        server = self.server
        authorization = self.headers.get("Authorization", "")
        token = authorization.removeprefix("Bearer ")
        seat = server.tokens.get(token) if authorization.startswith("Bearer ") else None
        if seat is None:
            self.error(401, "Use your private seat link")
            return
        try:
            data = {}
            if self.command == "POST":
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 8192:
                    raise ValueError("Expected a JSON object of at most 8192 bytes")
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict):
                    raise ValueError("Expected a JSON object")
            with server.lock:
                now = server.clock()
                table = server.table
                if self.path == "/ready":
                    if data.get("request_note_id") is True:
                        if "table_id" not in table.record:
                            table.record["table_id"] = secrets.token_hex(16)
                        server.note_seats.add(seat)
                    table.join(seat, now)
                elif self.path == "/choice":
                    table.submit(seat, data["revision"], data["choice"], now)
                elif self.path == "/say":
                    table.say(seat, data["revision"], data["text"], now)
                state = table.view(seat, now)
                if seat in server.note_seats:
                    state["table_id"] = table.record["table_id"]
                server.save()
        except DecisionConflict as e:
            self.error(409, str(e))
            return
        except (KeyError, ValueError, TypeError, RecursionError) as e:
            self.error(400, str(e))
            return
        self.send(200, json.dumps(state).encode())


def serve(args):
    rng = Random(1) if args.crossing else SystemRandom()
    if args.crossing:
        setup = read(WEB.parents[1] / "examples" / "crossing.json")["setup"]
    elif args.kit_counts is not None:
        kit = fixed_kit(Random(args.kit_seed), 16, *args.kit_counts)
        setup = paper_setup(rng, args.seats, kit=kit)
    else:
        setup = paper_setup(rng, args.seats)
    table = Table(setup, rng, args.seconds, args.discussion, color_teams=args.color_teams)
    with TableServer(table, args.save, args.port) as server:
        print(f"Referee record: {args.save.resolve()}")
        for token, seat in server.tokens.items():
            print(f"P{seat}  http://127.0.0.1:{server.server_port}/#{token}", flush=True)
        try:
            server.serve_forever(poll_interval=0.2)
        except KeyboardInterrupt:
            pass
        finally:
            with server.lock:
                server.save()
