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
from .ollama import INCOMPLETE_COMPACT, Seat, ServiceError, request
from .seat_tools import tile

CONTEXT_WINDOWS = (4096, 8192, 16384, 32768)

HISTORY_KINDS = (
    "draw",
    "place",
    "discard",
    "propose",
    "move_vote",
    "nominate",
    "eliminate_vote",
    "remark",
)


def history_page(
    history, *, before=None, after=None, turn=None, kind=None, speaker=None, voter=None, limit=6
):
    require(1 <= limit <= 20, "limit must be 1–20")
    require(
        kind is None or kind in HISTORY_KINDS,
        f"Choose a history kind from {', '.join(HISTORY_KINDS)}.",
    )
    require(turn is None or turn >= 1, "Game turns start at 1.")
    require(
        speaker is None or voter is None,
        "Query a speaker's remarks and a voter's revealed ballots separately.",
    )
    require(speaker is None or kind in (None, "remark"), "speaker filters remark entries.")
    require(
        voter is None or kind in (None, "move_vote", "eliminate_vote"),
        "voter filters move_vote and eliminate_vote entries.",
    )
    rows = []
    for index, item in enumerate(history, 1):
        if before is not None and index >= before or after is not None and index <= after:
            continue
        if turn is not None and item["turn"] != turn:
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
    "You play the same seat throughout a Footsteps game. Blue wins when the shared marker enters EXIT, "
    "whoever proposed the step. Red wins if the last movement opportunity ends short of EXIT or all "
    "Blue players are removed. Removed players share the team's result. Everyone knows both goals "
    "and the starting counts. Red knows the starting Red roster. Blue knows its own team. "
    "The builder places a held piece at an empty adjacent square, then separately proposes staying "
    "or taking one legal step from the marker. To step, the source must allow exit toward the "
    "destination and the destination must allow entry on its facing side. North increases y. "
    "Rotation is an absolute number of clockwise quarter turns from the printed face, 0 through 3. "
    "Living seats vote on steps; a tie follows the builder's own ballot. Removal requires a strict "
    "majority. Everyone hears public remarks, and either team can bluff. "
    "Call exactly one tool per reply. Use literal piece handles, seats and coordinates. "
    "Use history to check evidence and compact to retain private notes. The host clock continues "
    "during all calls. An accepted decision is final. Reading and preparing tiles are private."
)


def xy(point):
    return {"x": point[0], "y": point[1]}


HISTORY = function(
    "history",
    "Page observed events and attributed remarks by stable entry ID. kind may be remark, "
    "move_vote, eliminate_vote or another referee event. turn is the numbered game turn. speaker selects remarks; voter "
    "selects revealed ballots (null means timed out). Default is the latest six; after pages forward.",
    {
        "before": "integer",
        "after": "integer",
        "turn": "integer",
        "kind": "string",
        "speaker": "integer",
        "voter": "integer",
        "limit": "integer",
    },
)
HISTORY["function"]["parameters"]["required"] = []
HISTORY["function"]["parameters"]["properties"]["kind"]["enum"] = list(HISTORY_KINDS)


class Session:
    def __init__(
        self,
        seat,
        *,
        sleep=time.sleep,
        inspect_rotations=False,
        movement_context=False,
        wait_at_notice=True,
        context=8192,
    ):
        require(context in CONTEXT_WINDOWS, f"choose a context size from {CONTEXT_WINDOWS}")
        self.context = context
        self.seat = seat
        self.hand_mode = "fit" if inspect_rotations else "hand"
        self.wait_at_notice = wait_at_notice
        self.movement_context = movement_context
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

    def movement(self):
        s = self.snap
        state = s["state"]
        if state["stage"] == "propose" and s["choices"]:
            return {
                "marker": xy(state["marker"]),
                "goal": xy(state["goal"]),
                "legal_steps": [xy(p) for p in s["choices"]["to"] if p is not None],
            }
        if state["stage"] == "move_vote":
            return {
                "marker": xy(state["marker"]),
                "goal": xy(state["goal"]),
                "proposed_landing": xy(state["pending"]),
            }
        return {}

    def opportunity(self):
        s = self.snap
        movement = self.movement() if self.movement_context else {}
        return {
            **movement,
            **(
                {"nominee": s["state"]["pending"]}
                if s["state"]["stage"] == "eliminate_vote"
                else {}
            ),
            "cursor": self.cursor,
            "seat": s["seat"],
            "turn": s["state"]["turn"],
            "revision": s["revision"],
            "stage": s["state"]["stage"],
            "phase": s["phase"],
            "seconds_left_in_phase": int(s["seconds_left"])
            if s["seconds_left"] is not None
            else None,
            "can_speak": s["can_speak"],
            "owe_action": s["choices"] is not None,
            "last_history_id": len(s["history"]),
            "latest": [{"id": len(s["history"]), **s["history"][-1]}] if s["history"] else [],
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
        choices = s["choices"] or {}
        action_values = self.movement()
        if "at" in choices:
            action_values["empty_build_squares"] = [xy(p) for p in choices["at"]]
            if "origin" in choices:
                action_values["check_origins"] = [
                    {"origin_x": x, "origin_y": y} for x, y in choices["origin"]
                ]
        if "target" in choices:
            action_values["nomination_targets"] = [
                {"seat": v} for v in choices["target"] if v is not None
            ]
        board = []
        for pos, face in g["board"]:
            _, entrances, exits = tile(face)
            board.append({**xy(pos), "oriented_face": face, "entrances": entrances, "exits": exits})
        return {
            **self.opportunity(),
            **self.role(),
            "start": xy(g["start"]),
            "goal": xy(g["goal"]),
            "marker": xy(g["marker"]),
            "builder": g["actor"],
            "nominator": g["nominator"],
            "alive": g["alive"],
            "store_count": g["store_count"],
            "winner": g["winner"],
            "board": board,
            "held": [receipt(h, *v) for h, v in s["pieces"].items()],
            **action_values,
        }

    def reset(self, *, recovered=False):
        self.compact_failures = 0
        self.near_capacity = False
        self.messages = [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        **(
                            {
                                "context_recovery": "Two summary requests failed. Your last saved notes may predate recent events; use history to recover them."
                            }
                            if recovered
                            else {}
                        ),
                        "your_identity": self.role(),
                        "current": self.state(),
                        "your_private_player_authored_summary": self.summary,
                    }
                ),
            },
        ]

    def failed_compaction(self):
        self.compact_failures += 1
        if self.compact_failures < 2:
            return False
        self.refresh()
        self.reset(recovered=True)
        return True

    def tools(self):
        wait_tool = function(
            "wait",
            "Sleep without inference until a visible change after the last cursor you read. Waiting while owing a decision may time out.",
            {"after_cursor": "integer"},
        )
        if self.wait_at_notice:
            wait_tool["function"]["description"] = (
                "Call wait() to sleep until your seat sees a change since this update. "
                "An explicit after_cursor is optional. Waiting while owing a decision may time out."
            )
            wait_tool["function"]["parameters"]["required"] = []
        specs = [
            function("get_state", "Read your current board, held pieces and legal choices.", {}),
            function("get_role", "Read your authoritative private team assignment.", {}),
            HISTORY,
            function(
                "compact",
                "Save private evidence or plans you expect to need. Your identity, board, hand and original history remain available after compaction.",
                {"summary": "string"},
            ),
            wait_tool,
        ]
        if self.snap["can_speak"]:
            specs.append(
                function(
                    "speak", "Make one public remark, up to 500 characters.", {"text": "string"}
                )
            )
        if self.snap["choices"]:
            specs.extend(build_tools(self.snap, self.hand_mode))
        return specs

    def wait(self, after):
        require(0 <= after <= self.cursor, "use a cursor from this session")
        while self.cursor == after and self.snap["phase"] != "over":
            self.sleep(0.15)
            self.refresh()
        return self.opportunity()

    def execute(self, name, args, offered, revision):
        spec = next((t["function"] for t in offered if t["function"]["name"] == name), None)
        if spec is None:
            names = ", ".join(t["function"]["name"] for t in offered)
            raise ValueError("Choose one of the currently offered functions: " + names)
        require(isinstance(args, dict), "expected a function argument object")
        schema = spec["parameters"]
        types = {"integer": int, "boolean": bool, "string": str}
        require(
            set(schema["required"]) <= args.keys() <= schema["properties"].keys()
            and all(type(v) is types[schema["properties"][k]["type"]] for k, v in args.items()),
            f"{name} expects "
            + (
                ", ".join(
                    f"{k}: {spec['type']}" + ("" if k in schema["required"] else " (optional)")
                    for k, spec in schema["properties"].items()
                )
                or "no arguments"
            ),
        )
        notice_cursor = self.cursor
        self.refresh()
        if name == "history":
            return history_page(self.snap["history"], **args)
        if name == "get_role":
            return self.role()
        if name == "get_state":
            return self.state()
        if name == "compact":
            require(len(args["summary"]) <= 4096, "use at most 4096 characters")
            self.summary = args["summary"]
            self.reset()
            return {"compacted": True}
        if name == "wait":
            return self.wait(args.get("after_cursor", notice_cursor))
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
                self.hand_mode,
                orient,
            )
            if choice is None:
                if name in ("preview_placement", "inspect_rotations_at"):
                    result["at"] = xy(result["at"])
                    result["marker"] = xy(result.pop("marker_stays"))
                    if "legal_steps_after_build" in result:
                        result["legal_steps_after_build"] = [
                            xy(p) for p in result["legal_steps_after_build"]
                        ]
                return result
            self.seat.call("/choice", {"revision": revision, "choice": choice})
        self.refresh()
        return {
            "accepted": True,
            "action": name,
            "acted_at_revision": revision,
            "current": self.opportunity(),
        }

    def step(self, model, *, infer=request, budget=30, force_compact=False, compact_when=None):
        self.refresh()
        if self.snap["phase"] == "over":
            return None
        if self.snap["seat"] not in self.snap["state"]["alive"]:
            self.wait(self.cursor)
            return None
        revision = self.snap["revision"]
        force_compact = force_compact or bool(compact_when and compact_when(self.snap))
        offered = self.tools()
        notice = self.opportunity()
        recent = self.snap["history"][self.last_read :]
        if recent:
            notice["new_observations"] = [
                {"id": i, **r}
                for i, r in enumerate(
                    recent[-4:], len(self.snap["history"]) - min(len(recent), 4) + 1
                )
            ]
            notice["new_observation_count"] = len(recent)
        compact_required = force_compact or self.near_capacity
        if compact_required:
            offered = [t for t in offered if t["function"]["name"] == "compact"]
            notice["context_request"] = (
                "Call compact with a short private note about evidence or a plan. Your current state is restored automatically."
            )
        update = {"role": "user", "content": json.dumps(notice)}
        body = {
            "model": model,
            "stream": False,
            "think": False,
            "messages": [*self.messages, update],
            "tools": offered,
            "options": {
                "num_ctx": self.context,
                "num_predict": self.context // 10 if compact_required else 240,
                "temperature": 0,
                "seed": 1,
            },
        }
        started = time.monotonic()
        try:
            reply = infer(11434, "/api/chat", body, budget)
        except (TimeoutError, ServiceError) as exc:
            if (
                not compact_required
                and isinstance(exc, ServiceError)
                and exc.detail == INCOMPLETE_COMPACT
            ):
                # A voluntary compact hit the ordinary action allowance. Retry with the summary budget.
                self.near_capacity = True
                raise
            if (
                not compact_required
                or isinstance(exc, ServiceError)
                and exc.status < 500
                or not self.failed_compaction()
            ):
                raise
            return {
                "revision": revision,
                "tool": None,
                "arguments": {},
                "forced_compaction": force_compact,
                "result": {"context_recovered": True, "error": str(exc) or "request timed out"},
                "prompt_tokens": None,
                "reply_tokens": None,
                "inference_seconds": round(time.monotonic() - started, 3),
            }
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
        if compact_required and "error" in result and self.failed_compaction():
            result["context_recovered"] = True
        elif tokens > self.context * 6100 // 8192 and not result.get("compacted"):
            self.near_capacity = True
        return {
            "revision": revision,
            "forced_compaction": force_compact,
            "num_ctx": self.context,
            "num_predict": body["options"]["num_predict"],
            "opportunity": {
                key: notice[key]
                for key in (
                    "turn",
                    "stage",
                    "phase",
                    "can_speak",
                    "owe_action",
                    "seconds_left_in_phase",
                )
            },
            "tool": name,
            "tool_offered": any(t["function"]["name"] == name for t in offered),
            "arguments": args,
            "result": result,
            **{
                key: round(reply[field] / 1e9, 4)
                for key, field in (
                    ("prefill_seconds", "prompt_eval_duration"),
                    ("generation_seconds", "eval_duration"),
                )
                if isinstance(reply.get(field), int)
            },
            "prompt_tokens": tokens,
            "reply_tokens": reply.get("eval_count"),
            "inference_seconds": round(elapsed, 3),
        }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--model", required=True)
    cli.add_argument("--context", type=int, choices=CONTEXT_WINDOWS, default=8192)
    cli.add_argument(
        "--inspect-rotations",
        action="store_true",
        help="offer the four-orientation inspection tool when placing a tile",
    )
    cli.add_argument(
        "--movement-context",
        action="store_true",
        help="show the marker and available or proposed landing in movement updates",
    )
    cli.add_argument("--trace", type=Path, help="new private JSONL tool trace")
    args = cli.parse_args()
    seat = Seat(getpass("Private seat link: ").strip())
    seat.call("/ready", {})
    session = Session(
        seat,
        inspect_rotations=args.inspect_rotations,
        movement_context=args.movement_context,
        context=args.context,
    )

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
