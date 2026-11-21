"""One local model conversation, retained across an authenticated seat's turns."""

import argparse
import json
import time
from contextlib import nullcontext
from getpass import getpass
from http.client import HTTPException
from pathlib import Path

from .action_tools import apply_call, build_tools, function, receipt
from .decision_notes import open_private
from .game import require
from .ollama import RULES, Seat, ServiceError, request
from .seat_tools import tile


def history_page(history, *, before=None, after=None, kind=None, speaker=None, voter=None, limit=6):
    require(1 <= limit <= 20, "limit must be 1–20")
    rows = []
    for index, item in enumerate(history, 1):
        if before is not None and index >= before or after is not None and index <= after:
            continue
        if kind is not None and item["kind"] != kind:
            continue
        if speaker is not None and item.get("speaker") != speaker:
            continue
        if voter is not None and str(voter) not in item.get("ballots", {}):
            continue
        row = {"id": index, **item}
        if voter is not None:
            row["requested_ballot"] = item["ballots"][str(voter)]
        rows.append(row)
    return {
        "entries": rows[:limit] if after is not None else rows[-limit:],
        "more": len(rows) > limit,
    }


SYSTEM = (
    RULES + " A step onto EXIT wins for Blue whoever proposed it. Everyone knows the starting "
    "team sizes. Red knows the full Red roster; Blue is told only its own role. Eliminated "
    "players share the team outcome. All seats hear public remarks and either team may bluff. "
    "You play this same seat throughout. Call exactly one tool per reply. Use history to "
    "retrieve evidence and compact to preserve your own observations. Wait suspends you "
    "until your seat sees a change. Other players and the referee clock continue. "
    "An accepted action is final. Reads and preparations are private."
)
HISTORY = function(
    "history",
    "Page observed events and attributed remarks by stable entry ID. kind may be remark, "
    "move_vote, eliminate_vote or another referee event. speaker selects remarks; voter "
    "selects revealed ballots (null means timed out). Default is the latest six; after pages forward.",
    {
        "before": "integer",
        "after": "integer",
        "kind": "string",
        "speaker": "integer",
        "voter": "integer",
        "limit": "integer",
    },
)
HISTORY["function"]["parameters"]["required"] = []


class Session:
    def __init__(self, seat, *, sleep=time.sleep):
        self.seat = seat
        self.sleep = sleep
        self.cursor = 0
        self.stamp = None
        self.summary = ""
        self.last_read = 0
        self.near_capacity = False
        self.refresh()
        self.reset()

    def refresh(self):
        snap = self.seat.call("/session")
        stamp = (
            snap["revision"],
            len(snap["history"]),
            snap["phase"],
            snap["ready_count"],
            snap["voted"],
            snap["can_speak"],
            snap["pieces"],
        )
        if stamp != self.stamp:
            self.cursor += 1
            self.stamp = stamp
        self.snap = snap

    def opportunity(self):
        s = self.snap
        return {
            "cursor": self.cursor,
            "seat": s["seat"],
            "turn": s["state"]["turn"],
            "revision": s["revision"],
            "stage": s["state"]["stage"],
            "phase": s["phase"],
            "seconds_left_in_phase": s["seconds_left"],
            "can_speak": s["can_speak"],
            "owe_action": s["choices"] is not None,
            "last_history_id": len(s["history"]),
            "latest": s["history"][-1:],
        }

    def role(self):
        state = self.snap["state"]
        return {
            "seat": self.snap["seat"],
            "team": state["role"],
            "starting_red_count": state["red_count"],
            "starting_seats": state["player_count"],
            **({"red_teammates": state["teammates"]} if "teammates" in state else {}),
        }

    def state(self):
        s = self.snap
        g = s["state"]
        return {
            **self.opportunity(),
            **self.role(),
            **{
                k: g[k]
                for k in (
                    "start",
                    "goal",
                    "marker",
                    "actor",
                    "pending",
                    "nominator",
                    "alive",
                    "store_count",
                    "winner",
                )
            },
            "board_position_and_tile": [[p, tile(f)] for p, f in g["board"]],
            "held": [receipt(h, *v) for h, v in s["pieces"].items()],
            "legal": s["choices"],
        }

    def reset(self):
        self.near_capacity = False
        self.messages = [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "your_identity": self.role(),
                        "current": self.state(),
                        "your_private_player_authored_summary": self.summary,
                    }
                ),
            },
        ]

    def tools(self):
        specs = [
            function("get_state", "Read your current board, held pieces and legal choices.", {}),
            function("get_role", "Read your authoritative private team assignment.", {}),
            HISTORY,
            function(
                "compact",
                "Start a fresh conversation with your own private summary and current state. Original history stays available.",
                {"summary": "string"},
            ),
            function(
                "wait",
                "Sleep without inference until a visible change after the last cursor you read. Waiting while owing a decision may time out.",
                {"after_cursor": "integer"},
            ),
        ]
        if self.snap["can_speak"]:
            specs.append(
                function(
                    "speak", "Make one public remark, up to 500 characters.", {"text": "string"}
                )
            )
        if self.snap["choices"]:
            specs.extend(build_tools(self.snap, "hand"))
        return specs

    def wait(self, after):
        require(0 <= after <= self.cursor, "use a cursor from this session")
        while self.cursor == after and self.snap["phase"] != "over":
            self.sleep(0.15)
            self.refresh()
        return self.opportunity()

    def execute(self, name, args, offered, revision):
        spec = next((t["function"] for t in offered if t["function"]["name"] == name), None)
        require(spec is not None and isinstance(args, dict), "choose one available function")
        schema = spec["parameters"]
        types = {"integer": int, "boolean": bool, "string": str}
        require(
            set(schema["required"]) <= args.keys() <= schema["properties"].keys()
            and all(type(v) is types[schema["properties"][k]["type"]] for k, v in args.items()),
            "use the listed argument names and literal types",
        )
        self.refresh()
        if name == "history":
            return history_page(self.snap["history"], **args)
        if name == "get_role":
            return self.role()
        if name == "get_state":
            return self.state()
        if name == "compact":
            require(len(args["summary"]) <= 1600, "use at most 1600 characters")
            self.summary = args["summary"]
            self.reset()
            return {"compacted": True}
        if name == "wait":
            return self.wait(args["after_cursor"])
        require(revision == self.snap["revision"], "the decision changed; read the new opportunity")
        if name == "speak":
            self.seat.call("/say", {"revision": revision, "text": args["text"]})
        else:
            require(self.snap["choices"] is not None, "your decision is closed")

            def orient(handle, turns):
                self.seat.call(
                    "/orient", {"revision": revision, "piece": handle, "rotation": turns}
                )

            result, choice, _ = apply_call(
                name,
                args,
                self.snap["state"],
                self.snap["choices"],
                self.snap["pieces"].copy(),
                "hand",
                orient,
            )
            if choice is None:
                return result
            self.seat.call("/choice", {"revision": revision, "choice": choice})
        self.refresh()
        return {"accepted": True, **self.opportunity()}

    def step(self, model, *, infer=request, budget=30, force_compact=False):
        self.refresh()
        if self.snap["phase"] == "over":
            return None
        revision = self.snap["revision"]
        offered = self.tools()
        notice = self.opportunity()
        recent = self.snap["history"][self.last_read :]
        if recent:
            notice["new_observations"] = recent[-4:]
            notice["new_observation_count"] = len(recent)
        if force_compact or self.near_capacity:
            offered = [t for t in offered if t["function"]["name"] == "compact"]
            notice["context_request"] = (
                "Call compact with the private notes you want to carry forward."
            )
        update = {"role": "user", "content": json.dumps(notice)}
        body = {
            "model": model,
            "stream": False,
            "think": False,
            "messages": [*self.messages, update],
            "tools": offered,
            "options": {"num_ctx": 8192, "num_predict": 240, "temperature": 0, "seed": 1},
        }
        started = time.monotonic()
        reply = infer(11434, "/api/chat", body, budget)
        elapsed = time.monotonic() - started
        self.messages.append(update)
        self.last_read = len(self.snap["history"])
        calls = reply.get("message", {}).get("tool_calls", [])
        name = None
        args = {}
        try:
            require(
                reply.get("done_reason") != "length"
                and isinstance(calls, list)
                and len(calls) == 1
                and isinstance(calls[0], dict),
                "send exactly one complete tool call",
            )
            fn = calls[0].get("function")
            require(
                isinstance(fn, dict) and isinstance(fn.get("name"), str),
                "expected a named function",
            )
            name, args = fn["name"], fn.get("arguments")
            result = self.execute(name, args, offered, revision)
        except (ValueError, ServiceError) as exc:
            if isinstance(exc, ServiceError) and exc.status not in (400, 409):
                raise
            self.refresh()
            result = {"error": str(exc), "current": self.opportunity()}
        if name != "compact" or "error" in result:
            if name is None or not isinstance(args, dict):
                self.messages.append({"role": "user", "content": json.dumps(result)})
            else:
                self.messages.extend(
                    [
                        {"role": "assistant", "content": "", "tool_calls": calls},
                        {"role": "tool", "tool_name": name, "content": json.dumps(result)},
                    ]
                )
        tokens = reply.get("prompt_eval_count", 0)
        if tokens > 6100 and not result.get("compacted"):
            self.near_capacity = True
        return {
            "revision": revision,
            "tool": name,
            "arguments": args,
            "result": result,
            "prompt_tokens": tokens,
            "reply_tokens": reply.get("eval_count"),
            "inference_seconds": round(elapsed, 3),
        }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--model", required=True)
    cli.add_argument("--trace", type=Path, help="new private JSONL tool trace")
    args = cli.parse_args()
    seat = Seat(getpass("Private seat link: ").strip())
    seat.call("/ready", {})
    session = Session(seat)

    with open_private(args.trace) if args.trace else nullcontext() as trace:
        while session.snap["phase"] != "over":
            try:
                row = session.step(args.model)
            except (OSError, HTTPException) as exc:
                if isinstance(exc, ServiceError) and 400 <= exc.status < 500:
                    raise
                print(f"Session request failed ({exc}); refreshing.", flush=True)
                time.sleep(0.5)
                continue
            if trace and row:
                print(json.dumps(row), file=trace, flush=True)
        print("Winner:", session.snap["state"]["winner"])


if __name__ == "__main__":
    main()
