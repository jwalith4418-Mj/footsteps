"""Cross voter and proposer teams on the same legal ballot and fork its forecast before action."""

import argparse
import json
from collections import Counter
from copy import deepcopy
from itertools import combinations
from pathlib import Path
from random import Random

from experiments.horizon_votes import question
from experiments.persistent_proposals import FixtureSeat
from experiments.pregame_analysis import MODELS
from footsteps.board import distance, optimistic_length
from footsteps.ollama import request
from footsteps.record import new_record, read, replay
from footsteps.session import Session
from footsteps.table import Table

ROOT = Path(__file__).parent
CONTEXT = 16384
SOURCES = {
    "9901": "pivotal-votes/9b-game/five-9901-clear-r320.json",
    "13401": "open-tables/three/game.json",
}
CASES = (*SOURCES, "trap")
FIELDS = {"your_team": "string", "immediate_winner": "string", "blue_can_still_win": "boolean"}
FORECAST = (
    "Privately assess the pending step. Give your own team (blue or red). If the table approves "
    "the step, which team wins immediately (blue, red, or neither)? Including an immediate win, "
    "could Blue reach EXIT under that outcome with any legal future play?"
)


def trap():
    record = new_record(
        {
            "start": [-1, -1],
            "goal": [0, 0],
            "roles": ["blue", "red", "blue", "red", "blue"],
            "hands": [[255] for _ in range(5)],
            "store": [8, 255, 255],
        }
    )
    events = record["events"]
    for turn, (draw, at, step, approve) in enumerate(
        (
            ([8, 255], [0, -1], [0, -1], False),
            ([255, 255], [-1, 0], [-1, 0], True),
            ([255], [-2, 0], [0, 0], True),
        )
    ):
        events.extend(
            [
                {"kind": "draw", "tiles": draw},
                {"kind": "place", "at": at, "tile": draw[0], "rotation": 0},
            ]
        )
        if len(draw) == 2:
            events.append({"kind": "discard", "tile": 255})
        events.extend(
            [{"kind": "propose", "to": step}, {"kind": "move_vote", "votes": [approve] * 5}]
        )
        if turn < 2:
            events.extend({"kind": "nominate", "target": None} for _ in range(5))
    assert replay(record).winner == "blue"
    return record


def prefix(case):
    record = trap() if case == "trap" else read(ROOT / SOURCES[case])
    assert replay(record).winner == "blue"
    # Use the actual event history, but omit speech in every condition.
    cut = 4 if case == "trap" else len(record["events"]) - 1
    frozen = new_record(record["setup"])
    frozen["events"] = record["events"][:cut]
    g = replay(frozen)
    assert g.stage == "move_vote"
    assert (g.pending == g.goal) == (case != "trap")
    if case == "trap":
        assert distance(g.pending, g.goal) < distance(g.marker, g.goal)
        assert optimistic_length(g.board, g.pending, g.goal, len(g.store)) is None
    return frozen


def conditions(case):
    frozen = prefix(case)
    g = replay(frozen)
    other = {"13401": 2, "9901": 1, "trap": 1}[case]
    for voter in (g.actor, other):
        # Keep the nearest-to-observed legal roster for each role pair.
        rosters = sorted(
            combinations(range(len(g.roles)), g.roles.count("red")),
            key=lambda reds: sum((i in reds) != (t == "red") for i, t in enumerate(g.roles)),
        )
        seen = set()
        for reds in rosters:
            roles = ["red" if i in reds else "blue" for i in range(len(g.roles))]
            pair = roles[voter], roles[g.actor]
            if pair not in seen:
                seen.add(pair)
                yield voter, roles


def seat(case, voter, roles):
    frozen = prefix(case)
    table = Table(frozen["setup"] | {"roles": roles}, Random(101), seconds=60, discussion=0)
    for e in frozen["events"]:
        table.commit(e)
    peer = FixtureSeat(table, voter)
    for i in range(len(roles)):
        table.join(i, 0)
    assert voter in table.game.alive and table.game.stage == "move_vote"
    return Session(
        peer, sleep=peer.expire, inspect_rotations=True, movement_context=True, context=CONTEXT
    )


def trial(case, voter, roles, model):
    session = seat(case, voter, roles)
    table = session.seat.table
    builder = table.game.actor
    revision = table.revision
    fork = None

    def capture(port, path, body, budget):
        nonlocal fork
        fork = deepcopy(body["messages"])
        return request(port, path, body, budget)

    calls = []
    for _ in range(5):
        row = session.step(model, infer=capture, budget=60)
        calls.append(
            row["tool"] if row and row.get("tool_offered") else "unavailable_or_incomplete"
        )
        if voter in table.votes or table.revision != revision:
            break
    vote = table.votes.get(voter) if table.revision == revision else None
    assert fork is not None
    facts = question(fork, FORECAST, FIELDS, model=model, context=CONTEXT)
    return {
        "case": case,
        "voter": voter,
        "builder": builder,
        "team": roles[voter],
        "proposer_team": roles[builder],
        "model": model,
        "vote": vote,
        "forecast": facts,
        "calls": calls,
    }


def audit(rows):
    models = sorted({row["model"] for row in rows})
    assert models
    for model in models:
        for case in CASES:
            panel = [r for r in rows if (r["model"], r["case"]) == (model, case)]
            game = replay(prefix(case))
            expected = [(v, rs[v], rs[game.actor]) for v, rs in conditions(case)]
            assert Counter((r["voter"], r["team"], r["proposer_team"]) for r in panel) == Counter(
                expected
            )
            game.apply({"kind": "move_vote", "votes": [True] * len(game.alive)})
            immediate = game.winner or "neither"
            if game.winner is None:
                assert (
                    optimistic_length(game.board, game.marker, game.goal, len(game.store)) is None
                )
            blue_can_win = game.winner == "blue"
            counts = Counter()
            for row in panel:
                team = row["team"]
                correct = row["vote"] is ((team == "blue") == blue_can_win)
                forecast = row["forecast"]
                accurate = forecast == {
                    "your_team": team,
                    "immediate_winner": immediate,
                    "blue_can_still_win": blue_can_win,
                }
                counts.update(
                    rows=1,
                    cast=row["vote"] is not None,
                    aligned=correct,
                    role=forecast.get("your_team") == team,
                    immediate=forecast.get("immediate_winner") == immediate,
                    blue_can_win=forecast.get("blue_can_still_win") is blue_can_win,
                    accurate=accurate,
                    accurate_and_aligned=accurate and correct,
                )
            print(model, case, dict(counts))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--model", choices=MODELS, help="run inference; omit to audit saved rows")
    args = parser.parse_args()
    if args.model:
        with args.path.open("x") as out:
            for case in CASES:
                for voter, roles in conditions(case):
                    print(
                        json.dumps(trial(case, voter, roles, MODELS[args.model])),
                        file=out,
                        flush=True,
                    )
    audit([json.loads(line) for line in args.path.read_text().splitlines()])
