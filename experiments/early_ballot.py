"""Run or audit a three-seat comparison of fixed and early ballot clocks."""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.efficiency_audit import audit, decisions
from experiments.game_efficiency import MODEL, deal
from experiments.persistent_table import play
from footsteps.record import read
from footsteps.table import Table


def ballot_report(root):
    record = read(root / "game.json")
    votes = {
        (rev, seat): missed
        for rev, _, stage, seat, missed in decisions(record)
        if stage in ("move_vote", "eliminate_vote")
    }
    latest = {row["after_event"]: row["seat"] for row in record.get("remarks", [])}
    seen, accepted = set(), set()
    for path in root.glob("seat-*.jsonl"):
        seat = int(path.stem.split("-")[1])
        for line in path.read_text().splitlines():
            row = json.loads(line)
            rev = row["revision"]
            if rev in latest and row.get("ballot_prompt_last_speaker") == latest[rev]:
                seen.add((rev, seat))
                if row["tool"] in ("vote_move", "vote_removal") and not row["error"]:
                    accepted.add((rev, seat))
    with_remarks = {key for key in votes if key[0] in latest}
    timely = {key for key in with_remarks if not votes[key]}
    return {
        "timely_votes": sum(not missed for missed in votes.values()),
        "owed_votes": len(votes),
        "remark_available": len(with_remarks),
        "remark_in_vote_prompt": len(seen & with_remarks),
        "timely_votes_with_remarks": len(timely),
        "remark_in_accepted_vote_prompt": len(accepted & timely),
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=Path)
    cli.add_argument(
        "private",
        type=Path,
        nargs="?",
        help="new owner-only trace directory; omit to audit saved game",
    )
    cli.add_argument("--early-ballot", action="store_true")
    args = cli.parse_args()
    if args.private:
        seed = 11301
        table = Table(
            deal("social", seed), Random(f"draw/{seed}"), 45, 30, early_ballot=args.early_ballot
        )
        play(args.root, args.private, MODEL, 32768, 45, 30, table=table)
    print(json.dumps(audit(args.root) | ballot_report(args.root), indent=2))
