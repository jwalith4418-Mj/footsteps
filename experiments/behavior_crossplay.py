"""Cash out trust in three-seat games with two publicly accountable scripted opponents."""

import argparse
import csv
import json
import secrets
from copy import deepcopy
from pathlib import Path
from random import Random

from experiments.behavior_context import STRATEGIES
from experiments.behavior_probe import decide
from experiments.skill_probe import MODEL
from experiments.social_prompt import progress_ballots
from experiments.turn_plans import plans, score
from footsteps.board import distance
from footsteps.decision_notes import open_private
from footsteps.game import Game
from footsteps.ollama import infer, request
from footsteps.record import replay
from footsteps.table import BALLOTS, Table, paper_setup


def vote_intent(state):
    return distance(state["pending"], state["goal"]) < distance(state["marker"], state["goal"])


def suspects(snap):
    votes = progress_ballots(snap)
    # Only an identified, explicit no on a closer move counts to this opponent.
    return {
        s
        for s in snap["state"]["alive"]
        if s != snap["seat"]
        and any(
            row["from_distance"] > row["to_distance"] and row["votes"].get(f"P{s}") == "no"
            for row in votes
        )
    }


def scripted(snap, walk):
    state, options = snap["state"], snap["choices"]
    stage = state["stage"]
    if stage == "propose":
        return {"to": None if state["role"] == "bad" else walk}
    if stage == "move_vote":
        return {"vote": vote_intent(state)}
    evidence = suspects(snap)
    if stage == "nominate":
        return {"target": next((s for s in options["target"] if s in evidence), None)}
    return {"vote": state["pending"] in evidence}


def game(seed, seat, role, store, strategy, model, output, notes):
    bad = seat if role == "bad" else 3 - seat
    setup = paper_setup(Random(seed), 3)
    setup["store"] = setup["store"][:store]
    setup["roles"] = ["bad" if s == bad else "good" for s in range(3)]
    table = Table(setup, Random(f"draw/{seed}"), discussion=1)
    table.record["table_id"] = secrets.token_hex(16)
    pick = Random(f"build/{seed}")
    for s in range(3):
        table.join(s, 0)
    walk = None
    while not table.game.winner:
        now = table.opens
        if table.game.stage == "move_vote":
            for s in table.game.alive:
                if s == seat:
                    continue
                before = table.view(s, now - table.discussion)
                intent = "yes" if vote_intent(before["state"]) else "no"
                table.say(
                    s,
                    table.revision,
                    f"I intend to vote {intent}. I will nominate players who vote no on a step toward EXIT.",
                    now - table.discussion,
                )
        snapshots = [table.view(s, now) for s in range(3)]
        for snap in snapshots:
            if not (choices := snap["choices"]):
                continue
            s, state = snap["seat"], snap["state"]
            stage = state["stage"]
            if stage == "place":
                state["draw_count"] = int(snap["history"][-1]["text"].split()[2])
                menu = plans(state, choices)
                best = min(map(score, menu))
                plan = pick.choice([p for p in menu if score(p) == best])
                choice, walk = plan["place"], plan["to"]
            elif stage == "discard":
                choice = {"tile": min(choices["tile"], key=lambda f: (f.bit_count(), f))}
            elif s != seat:
                choice = scripted(snap, walk)
            else:
                snap["table_id"] = table.record["table_id"]
                if stage == "propose":
                    # Earlier ablations hold proposals fixed. The final candidate also frames its own walk.
                    choice = infer(
                        snap,
                        model,
                        30,
                        guided=True,
                        social_guidance=strategy == "payoff-trust",
                        outcome_policy=strategy == "assisted",
                        named_moves=True,
                        no_think=True,
                        note_file=notes,
                    )
                else:
                    choice = decide(snap, model, strategy, notes)
            table.submit(s, snap["revision"], choice, now)
    assert replay(table.record).winner == table.game.winner
    output.write_text(json.dumps(table.record, separators=(",", ":")) + "\n")
    return metrics(table.record, seat)


def metrics(record, seat):
    g = Game(record["setup"])
    no = None
    out = None
    builds = 0
    pivotal = 0
    for e in record["events"]:
        if g.stage == "place" and g.actor == seat:
            builds += 1
        if g.stage == "move_vote" and g.turn == 1:
            no = not e["votes"][g.alive.index(seat)]
        turn_before = g.turn
        alive = g.alive.copy()
        if g.stage in BALLOTS and seat in alive:
            # Evaluate the opposite ballot under the actual other votes using the referee.
            fork = deepcopy(g)
            votes = e["votes"].copy()
            votes[alive.index(seat)] = not votes[alive.index(seat)]
            fork.apply({**e, "votes": votes})
            g.apply(e)
            pivotal += (g.marker, g.alive, g.winner) != (fork.marker, fork.alive, fork.winner)
        else:
            g.apply(e)
        if seat in alive and seat not in g.alive:
            out = turn_before
    return {
        "opening_no": no,
        "removed_turn": out,
        "builds": builds,
        "pivotal_ballots": pivotal,
        "winner": g.winner,
        "turns": g.turn,
    }


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--model", default=MODEL)
    cli.add_argument("--strategy", choices=STRATEGIES, required=True)
    cli.add_argument("--seeds", type=int, nargs="+", required=True)
    cli.add_argument("--store", type=int, choices=(6, 10), required=True)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--private-notes", type=Path, required=True)
    args = cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    args.private_notes.mkdir(parents=True, mode=0o700, exist_ok=False)
    request(
        11434,
        "/api/generate",
        {"model": args.model, "stream": False, "options": {"num_ctx": 4096}},
        180,
    )
    with (args.out / "results.csv").open("x") as f:
        writer = None
        for seed in args.seeds:
            for seat in (1, 2):
                for role in ("bad", "good"):
                    name = f"{seed}-P{seat}-{role}"
                    with open_private(args.private_notes / (name + ".jsonl")) as notes:
                        result = game(
                            seed,
                            seat,
                            role,
                            args.store,
                            args.strategy,
                            args.model,
                            args.out / (name + ".json"),
                            notes,
                        )
                    row = {"seed": seed, "seat": seat, "role": role, **result}
                    if writer is None:
                        writer = csv.DictWriter(f, row, lineterminator="\n")
                        writer.writeheader()
                    writer.writerow(row)
                    f.flush()
                    print(name, result, flush=True)


if __name__ == "__main__":
    main()
