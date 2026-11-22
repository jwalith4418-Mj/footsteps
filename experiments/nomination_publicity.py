"""Observe named nominations on fresh deals and locate the strict-majority boundary."""

import argparse
import json
from functools import partial
from pathlib import Path
from random import Random

from experiments.game_efficiency import MODEL
from experiments.horizon_votes import question
from experiments.persistent_proposals import FixtureSeat
from experiments.persistent_table import play
from experiments.thinking_game import BallotSession, share_usage
from footsteps.game import with_exit_origin
from footsteps.record import read, replay, starting_game
from footsteps.session import Session
from footsteps.table import Table, paper_setup

DEALS = {14101: 4, 14102: 5}


def deal(seed):
    seats = DEALS[seed]
    setup = paper_setup(Random(seed), seats)
    roles = ["blue"] * (seats - 2) + ["red"] * 2
    Random(f"roles/{seed}").shuffle(roles)
    setup.update(roles=roles, goal=[2, 0], store=setup["store"][:3])
    return Table(with_exit_origin(setup), Random(f"draw/{seed}"), 60, 30, early_ballot=True)


def run(seed, output, owner):
    play(
        output,
        owner,
        MODEL,
        16384,
        60,
        30,
        table=deal(seed),
        session_class=partial(
            BallotSession, allowance=768, private=owner, thinking_tool="nominate"
        ),
    )
    share_usage(output, owner, "nomination-thinking.jsonl")


def first_majority(record):
    """Return the earliest revision with a living Red majority (zero denotes setup)."""
    game = starting_game(record)
    for revision in range(len(record["events"]) + 1):
        if sum(game.roles[i] == "red" for i in game.alive) * 2 > len(game.alive):
            return revision
        if revision < len(record["events"]):
            game.apply(record["events"][revision])
    return None


def majority_witness(approve):
    """Fork the worked crossing so P1 can propose EXIT while outnumbered two to one."""
    record = read(Path(__file__).resolve().parents[1] / "examples/crossing.json")
    record["setup"]["roles"] = ["red", "blue", "blue", "red"]
    record["events"][5] = {"kind": "nominate", "target": 2}
    record["events"][6] = {"kind": "eliminate_vote", "votes": [True, True, False, True]}
    # P2 is removed, P3 and P0 pass, and P1 builds as in the original history.
    record["events"][-1] = {"kind": "move_vote", "votes": [approve, True, False]}
    return record


def majority_ballot(seat):
    record = majority_witness(False)
    table = Table(record["setup"], Random(1), seconds=60, discussion=0)
    for event in record["events"][:-1]:
        table.commit(event)
    peer = FixtureSeat(table, seat)
    for other in range(len(table.game.roles)):
        table.join(other, 0)
    session = Session(
        peer, sleep=peer.expire, inspect_rotations=True, movement_context=True, context=16384
    )
    revision = table.revision
    calls = []
    for _ in range(5):
        row = session.step(MODEL, budget=60)
        calls.append(
            {
                "tool": row["tool"] if row and row.get("tool_offered") else None,
                "tokens": row["reply_tokens"] if row else None,
                "seconds": row["inference_seconds"] if row else None,
            }
        )
        if seat in table.votes or table.revision != revision:
            break
    vote = table.votes.get(seat) if table.revision == revision else None
    return {"seat": seat, "team": table.game.roles[seat], "vote": vote, "calls": calls}


def archived_majorities(root):
    """Count completed distinct multi-Red referee histories, ignoring prose and table IDs."""
    seen = set()
    for path in sorted(root.rglob("*.json")):
        data = json.loads(path.read_text())
        if not isinstance(data, dict) or not {"format", "setup", "events"} <= data.keys():
            continue
        record = read(path)
        key = json.dumps([record["setup"], record["events"]], sort_keys=True)
        if record["setup"]["roles"].count("red") < 2 or key in seen:
            continue
        game = replay(record)
        if game.winner:
            seen.add(key)
            yield {
                "path": str(path),
                "majority_at": first_majority(record),
                "end": len(record["events"]),
                "winner": game.winner,
            }


def readback(record, team):
    # The same previously unseen nomination, from P1's private seat, with no speech cues.
    setup = dict(record["setup"])
    roles = setup["roles"].copy()
    if roles[1] != team:
        other = roles.index(team)
        roles[1], roles[other] = roles[other], roles[1]
    setup["roles"] = roles
    table = Table(setup, Random(1), discussion=0)
    for event in record["events"]:
        if table.game.stage == "nominate":
            break
        table.commit(event)
    assert table.game.stage == "nominate" and table.game.queue[0] == 1
    peer = FixtureSeat(table, 1)
    for i in table.game.alive:
        table.join(i, 0)
    session = Session(peer, inspect_rotations=True, movement_context=True, context=16384)
    prompt = (
        "Pause before acting and answer privately about the table rules. "
        "If you use nominate(seat=0) without speaking, what exactly will P2 see immediately "
        "and what happens to P0 then? If you pass instead, what exactly will P2 see? "
        "If a removal ballot opens and only P0 has voted, what can P2 see of P0's vote "
        "at that moment and after the ballot closes? Use one short sentence per field."
    )
    # This is a separate readback, with the same offered schemas rendered for reference.
    messages = [*session.messages, {"role": "user", "content": json.dumps(session.tools())}]
    fields = dict.fromkeys(("nomination", "pass", "before_reveal", "after_reveal"), "string")
    return {
        "seat": 1,
        "team": team,
        "revision": table.revision,
        "answer": question(messages, prompt, fields, model=MODEL, context=16384),
    }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    modes = cli.add_subparsers(dest="command", required=True)
    live = modes.add_parser("play")
    live.add_argument("seed", type=int, choices=DEALS)
    live.add_argument("output", type=Path)
    live.add_argument("owner", type=Path)
    probe = modes.add_parser("readback")
    probe.add_argument("record", type=Path)
    probe.add_argument("output", type=Path)
    modes.add_parser("witness")
    ballot = modes.add_parser("majority-ballot")
    ballot.add_argument("output", type=Path)
    archive = modes.add_parser("archive")
    archive.add_argument("root", type=Path)
    audit = modes.add_parser("majority")
    audit.add_argument("record", type=Path, nargs="+")
    args = cli.parse_args()
    if args.command == "play":
        run(args.seed, args.output, args.owner)
    elif args.command == "majority-ballot":
        with args.output.open("x") as out:
            for seat in (0, 1, 3):
                print(json.dumps(majority_ballot(seat)), file=out, flush=True)
    elif args.command == "witness":
        for approve in (False, True):
            record = majority_witness(approve)
            print(
                "P0 votes",
                approve,
                "majority at",
                first_majority(record),
                "winner",
                replay(record).winner,
            )
    elif args.command == "archive":
        for row in archived_majorities(args.root):
            print(json.dumps(row))
    elif args.command == "readback":
        with args.output.open("x") as out:
            for team in ("red", "blue"):
                print(json.dumps(readback(read(args.record), team)), file=out, flush=True)
    else:
        for path in args.record:
            print(path, first_majority(read(path)))
