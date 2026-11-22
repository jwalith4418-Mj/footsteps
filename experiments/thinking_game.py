"""Give a persistent seat a bounded thinking allowance on a selected live decision."""

import argparse
import hashlib
import json
from functools import partial
from pathlib import Path
from random import Random

from experiments.game_efficiency import MODEL
from experiments.open_tables import DEALS
from experiments.persistent_table import play
from footsteps.decision_notes import open_private
from footsteps.game import with_exit_origin
from footsteps.session import Session
from footsteps.table import Table, paper_setup


def attach_result(note, row):
    if note["stage"] == "nominate":
        action = row["tool"] if row and row["result"].get("accepted") else None
        if action == "nominate":
            note["label"] += f" · nominated P{row['arguments']['seat']}"
        elif action == "pass_nomination":
            note["label"] += " · passed"
        else:
            note["label"] += " · no nomination committed"
        return note
    vote = None
    if row and row["tool"] == "vote_move" and row["result"].get("accepted"):
        vote = row["arguments"]["approve"]
    note["submitted_vote"] = vote
    if vote is not None:
        note["label"] += " · submitted " + ("Yes" if vote else "No")
    elif row is None or "error" in row["result"]:
        note["label"] += " · no accepted action"
    return note


class BallotSession(Session):
    def __init__(self, peer, *, allowance, private, thinking_tool="vote_move", **kwargs):
        self.thinking_tool = thinking_tool
        self.allowance = allowance
        registration = peer.call("/ready", {"request_note_id": True})
        self.table_id = registration["table_id"]
        self.notes = private / f"thinking-{registration['seat']}.jsonl"
        with open_private(self.notes):
            pass
        self.ballot_revision = None
        self.used = 0
        self.previous_thoughts = []
        super().__init__(peer, **kwargs)

    def step(self, model, *, infer, **kwargs):
        note = None
        returned = None
        actual_limit = None

        def during_vote(port, path, body, timeout):
            nonlocal returned, actual_limit, note
            offered_choice = any(t["function"]["name"] == self.thinking_tool for t in body["tools"])
            rev = self.snap["revision"]
            if rev != self.ballot_revision:
                self.ballot_revision = rev
                self.used = 0
                for assistant in self.previous_thoughts:
                    assistant.pop("thinking", None)
                self.previous_thoughts.clear()
            left = self.allowance - self.used
            if not offered_choice or left <= 0:
                return infer(port, path, body, timeout)
            actual_limit = left
            body = body | {"think": True, "options": body["options"] | {"num_predict": left}}
            reply = infer(port, path, body, timeout)
            returned = reply["message"]
            tokens = reply["eval_count"]
            self.used += tokens
            calls = returned.get("tool_calls")
            tool = "no tool"
            if isinstance(calls, list) and calls and isinstance(calls[0], dict):
                function = calls[0].get("function")
                if isinstance(function, dict):
                    offered = {t["function"]["name"] for t in body["tools"]}
                    name = function.get("name")
                    tool = name if isinstance(name, str) and name in offered else "unavailable tool"
            stop = reply.get("done_reason")
            label = "Nomination" if self.thinking_tool == "nominate" else "Movement ballot"
            note = {
                "kind": "thinking",
                "version": 1,
                "table_id": self.table_id,
                "seat": self.snap["seat"],
                "turn": self.snap["state"]["turn"],
                "stage": self.snap["state"]["stage"],
                "revision": rev,
                "model": model,
                "label": f"{label} · {tokens}/{left} tokens · {stop} · {tool}",
                "thinking": returned.get("thinking", ""),
                "limit": left,
                "tokens": tokens,
                "stop": stop,
                "seconds": round(reply.get("total_duration", 0) / 1e9, 3),
                "tool": tool,
            }
            return reply

        row = None
        try:
            row = super().step(model, infer=during_vote, **kwargs)
        finally:
            if note is not None:
                with self.notes.open("a", encoding="utf8") as sink:
                    print(json.dumps(attach_result(note, row)), file=sink)
        if returned is not None:
            row["num_predict"] = actual_limit
            if len(self.messages) >= 2:
                assistant = self.messages[-2]
                if assistant["role"] == "assistant" and assistant.get("tool_calls") == returned.get(
                    "tool_calls"
                ):
                    assistant["thinking"] = returned.get("thinking", "")
                    self.previous_thoughts.append(assistant)
        return row


def share_usage(root, private, filename="movement-thinking.jsonl"):
    with (root / filename).open("x") as output:
        for sidecar in sorted(private.glob("thinking-*.jsonl")):
            for line in sidecar.read_text().splitlines():
                row = json.loads(line)
                receipt = {
                    k: row[k]
                    for k in (
                        "seat",
                        "revision",
                        "model",
                        "limit",
                        "tokens",
                        "stop",
                        "seconds",
                        "tool",
                    )
                }
                if "submitted_vote" in row:
                    receipt["submitted_vote"] = row["submitted_vote"]
                trace = row["thinking"]
                receipt["thinking_chars"] = len(trace)
                receipt["thinking_sha256"] = hashlib.sha256(trace.encode()).hexdigest()
                print(json.dumps(receipt), file=output)


def run(root, private, allowance):
    seed, seats, offset, size = DEALS["three"]
    setup = paper_setup(Random(seed), seats)
    setup.update(goal=offset, store=setup["store"][:size])
    table = Table(with_exit_origin(setup), Random(f"draw/{seed}"), 60, 30, early_ballot=True)
    play(
        root,
        private,
        MODEL,
        16384,
        60,
        30,
        table=table,
        session_class=partial(BallotSession, allowance=allowance, private=private),
    )

    share_usage(root, private)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=Path)
    cli.add_argument("private", type=Path)
    cli.add_argument("--allowance", type=int, default=768)
    args = cli.parse_args()
    if not 0 < args.allowance <= 8192:
        cli.error("choose a movement ballot allowance between 1 and 8192")
    run(args.root, args.private, args.allowance)
