"""Host a fresh five-seat social game with one independently operated private seat."""

import argparse
import json
import secrets
import shutil
import time
from pathlib import Path
from random import Random

from experiments.skill_probe import MODEL
from experiments.social_evidence import social_game, write_rows
from footsteps.decision_notes import open_private, save_note
from footsteps.ollama import tile
from footsteps.table import fixed_kit

HERE = Path(__file__).resolve().parent


class Guest:
    def __init__(self, exchange, seat, debrief_path):
        self.root = exchange
        self.debrief_path = debrief_path
        self.seat = seat
        self.sequence = 0
        self.history_count = 0

    def ask(self, kind, snap):
        self.sequence += 1
        state = snap["state"]
        packet = {
            "id": self.sequence,
            "kind": kind,
            "seat": self.seat,
            "revision": snap["revision"],
            "new_history": snap["history"][self.history_count :],
            "alive": state["alive"],
            "marker": state["marker"],
        }
        self.history_count = len(snap["history"])
        if kind == "debrief":
            packet["instructions"] = (
                "Play has ended. Write your pre-reveal observations and seat-by-seat inferences in observation."
            )
        else:
            packet.update(
                role=state["role"].capitalize(),
                initial_red=state["red_count"],
                players=state["player_count"],
                turn=state["turn"],
                stage=state["stage"],
                builder=state["actor"],
                goal=state["goal"],
                store_count=state["store_count"],
                pending=state["pending"],
                board=state["board"],
                hand=[tile(f) for f in state["hand"]],
            )
            if state["role"] == "red":
                packet["other_red_seats"] = state["teammates"]
            if kind == "choice":
                packet["legal"] = snap["choices"]
            if kind == "arrival":
                packet["instructions"] = (
                    "Acknowledge with a private observation. In this table's trial only the nominator may speak before an elimination ballot. Movement has no discussion. Hand triples show printed face, entrances, exits. Board faces already include rotation."
                )
        path = self.root / f"{self.sequence:04}.request.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(packet, separators=(",", ":")))
        tmp.replace(path)
        reply = self.root / f"{self.sequence:04}.reply.json"
        while not reply.exists():
            time.sleep(0.15)
        return json.loads(reply.read_text())

    def choose(self, snap, sink):
        reply = self.ask("choice", snap)
        choice = reply["choice"]
        save_note(sink, snap, "Blinded guest", choice, reply["observation"], [])
        return choice

    def finish(self, snap):
        response = self.ask("debrief", snap)
        with open_private(self.debrief_path) as out:
            out.write(response["observation"] + "\n")
        (self.root / "finished").touch()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--exchange", type=Path, required=True)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--private", type=Path, required=True)
    cli.add_argument("--seed", type=int, help="fresh random seed when omitted")
    cli.add_argument("--start-origin", action="store_true", help="use historical guest coordinates")
    args = cli.parse_args()
    args.exchange.mkdir(parents=True, exist_ok=True, mode=0o700)
    if any(args.exchange.iterdir()):
        cli.error("use a fresh empty guest exchange directory")
    args.exchange.chmod(0o700)
    shutil.copyfile(HERE / "guest_client.py", args.exchange / "seat.py")
    shutil.copyfile(HERE.parent / "docs/rules.md", args.exchange / "rules.md")
    args.out.mkdir(parents=True, exist_ok=False)
    args.private.mkdir(parents=True, exist_ok=False, mode=0o700)
    seed = secrets.randbits(32) if args.seed is None else args.seed
    roles = ["blue"] * 3 + ["red"] * 2
    Random(f"roles/{seed}").shuffle(roles)
    seat = Random(f"guest/{seed}").randrange(len(roles))
    guest = Guest(args.exchange, seat, args.private / "guest-debrief.md")
    stem = f"{seed}-red" + "+".join(str(s) for s, r in enumerate(roles) if r == "red")
    (args.private / "run.json").write_text(json.dumps({"seed": seed, "guest": seat}))
    rows = social_game(
        seed,
        roles,
        MODEL,
        args.out / f"{stem}.json",
        args.private / f"{stem}.jsonl",
        "receipt",
        debate=True,
        model_floor=True,
        outcome_policy=True,
        paired_fifth_hand=True,
        kit=fixed_kit(Random(8700), 16, 29, 29),
        guest=guest,
        exit_origin=not args.start_origin,
    )
    write_rows(args.out / "choices.csv", rows)


if __name__ == "__main__":
    main()
