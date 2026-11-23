"""Host one private guest terminal alongside ordinary persistent Ollama seats."""

import argparse
import json
import secrets
import shutil
from pathlib import Path
from random import Random
from time import sleep

from experiments.game_efficiency import MODEL
from experiments.guest_game import Guest
from experiments.persistent_table import play
from footsteps.decision_notes import save_note
from footsteps.game import with_exit_origin
from footsteps.ollama import ServiceError
from footsteps.table import Table, paper_setup


class LiveGuest(Guest):
    def play(self, peer, notes):
        snap = peer.call("/ready", {"request_note_id": True})
        last_discussion = None
        while snap["phase"] != "over":
            rev = snap["revision"]
            speaking = snap["can_speak"] and rev != last_discussion
            if speaking or snap["choices"]:
                kind = "speech" if speaking else "choice"
                reply = self.ask(kind, snap, timeout=snap["seconds_left"])
                if speaking:
                    last_discussion = rev
                if reply is not None:
                    try:
                        if speaking and reply["speech"].strip():
                            peer.call("/say", {"revision": rev, "text": reply["speech"]})
                        elif not speaking:
                            peer.call("/choice", {"revision": rev, "choice": reply["choice"]})
                            save_note(
                                notes,
                                snap,
                                "Blinded guest",
                                reply["choice"],
                                reply["observation"],
                                [],
                            )
                    except ServiceError as exc:
                        if exc.status != 409:
                            raise
            else:
                sleep(0.15)
            snap = peer.call("/session")
        self.finish(snap, timeout=90)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=Path)
    cli.add_argument("private", type=Path)
    cli.add_argument("exchange", type=Path)
    cli.add_argument("--seed", type=int)
    args = cli.parse_args()
    args.exchange.mkdir(mode=0o700, exist_ok=False)
    here = Path(__file__).parent
    shutil.copyfile(here / "guest_client.py", args.exchange / "seat.py")
    shutil.copyfile(here.parent / "docs/rules.md", args.exchange / "rules.md")
    seed = secrets.randbits(32) if args.seed is None else args.seed
    floor = paper_setup(Random(seed), 4)
    floor.update(goal=[2, 1], store=floor["store"][:6])
    guest = LiveGuest(
        args.exchange, Random(f"guest/{seed}").randrange(4), args.private / "debrief.md"
    )
    table = Table(with_exit_origin(floor), Random(f"draw/{seed}"), 90, 40, early_ballot=True)
    play(args.root, args.private, MODEL, 16384, 90, 40, table=table, guest=guest)
    (args.root / "deal.json").write_text(json.dumps({"seed": seed, "guest": guest.seat}) + "\n")


if __name__ == "__main__":
    main()
