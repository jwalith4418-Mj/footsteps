"""Run or audit matched social games with fixed or early ballot clocks."""

import argparse
import json
from pathlib import Path
from random import Random

from experiments.efficiency_audit import audit, decisions, service
from experiments.game_efficiency import MODEL, deal
from experiments.persistent_table import play
from footsteps.record import read
from footsteps.table import Table, paper_setup


def ballot_report(root):
    record = read(root / "game.json")
    votes = {
        (rev, seat): missed
        for rev, _, stage, seat, missed in decisions(record)
        if stage in ("move_vote", "eliminate_vote")
    }
    latest = {row["after_event"]: row["seat"] for row in record.get("remarks", [])}
    seen, accepted = set(), set()
    polls = repeated = 0
    poll_seconds = required_queue_max = 0
    for path in root.glob("seat-*.jsonl"):
        seat = int(path.stem.split("-")[1])
        previous = None
        for line in path.read_text().splitlines():
            row = json.loads(line)
            rev = row["revision"]
            notice = row.get("opportunity", {})
            if notice.get("owe_action"):
                required_queue_max = max(required_queue_max, row["queue_seconds"])
            query = None
            if (
                row["tool"] == "history"
                and not row["error"]
                and notice.get("stage") in ("move_vote", "eliminate_vote")
                and row.get("filters", {}).get("kind") == notice["stage"]
            ):
                polls += 1
                poll_seconds += service(row)
                query = (rev, notice["phase"], row["filters"], row["entry_ids"])
                repeated += query == previous
            previous = query
            if rev in latest and row.get("ballot_prompt_last_speaker") == latest[rev]:
                seen.add((rev, seat))
                if row["tool"] in ("vote_move", "vote_removal") and not row["error"]:
                    accepted.add((rev, seat))
    with_remarks = {key for key in votes if key[0] in latest}
    timely = {key for key in with_remarks if not votes[key]}
    return {
        "timely_votes": sum(not missed for missed in votes.values()),
        "owed_votes": len(votes),
        "matching_ballot_history_reads": polls,
        "matching_ballot_history_seconds": round(poll_seconds, 2),
        "consecutive_identical_ballot_pages": repeated,
        "max_required_queue_seconds": round(required_queue_max, 2),
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
    cli.add_argument(
        "--extra-blue",
        action="store_true",
        help="seat P3 with two unused kit tiles, preserving the reference private deals and store",
    )
    args = cli.parse_args()
    if args.private:
        seed = 11301
        floor = deal("social", seed)
        if args.extra_blue:
            spare = paper_setup(Random(seed), 3)["store"][len(floor["store"]) :]
            floor["roles"].append("blue")
            floor["hands"].append(spare[:2])
        table = Table(floor, Random(f"draw/{seed}"), 45, 30, early_ballot=args.early_ballot)
        play(args.root, args.private, MODEL, 32768, 45, 30, table=table)
    print(json.dumps(audit(args.root) | ballot_report(args.root), indent=2))
