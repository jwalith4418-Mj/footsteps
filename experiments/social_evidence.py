"""Three-seat social decisions against an overt dissenter on the standard paper floor."""

import argparse
import csv
import json
import secrets
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
from random import Random

from experiments.skill_probe import MODEL
from experiments.social_prompt import advocate, social_choice
from experiments.turn_plans import plans, score
from footsteps.board import distance
from footsteps.decision_notes import open_private
from footsteps.ollama import infer, request
from footsteps.record import replay
from footsteps.table import PAPER_KIT, Table, fixed_kit, paper_setup


def approach(state):
    return distance(state["pending"], state["goal"]) < distance(state["marker"], state["goal"])


def social_game(
    seed,
    roles,
    model,
    output,
    notes,
    arm,
    debate=False,
    bad_brief=False,
    model_floor=False,
    social_guidance=False,
    outcome_policy=False,
    kit=PAPER_KIT,
):
    def elimination(snap, sink):
        if outcome_policy:
            return infer(snap, model, 30, outcome_policy=True, no_think=True, note_file=sink)
        return social_choice(
            snap,
            model,
            arm,
            sink,
            bad_brief=bad_brief,
            strategy="payoff-trust" if social_guidance else "baseline",
        )

    seats = range(len(roles))
    bad = "+".join(str(s) for s in seats if roles[s] == "bad")
    setup = paper_setup(Random(seed), len(roles), kit=kit)
    setup["roles"] = roles
    table = Table(setup, Random(f"draw/{seed}"), discussion=1)
    table.record["table_id"] = secrets.token_hex(16)
    for s in seats:
        table.join(s, 0)
    pick = Random(f"build/{seed}")
    destination = None
    calls = []
    nominator = None
    with ExitStack() as files:
        sink = files.enter_context(open_private(notes))
        if debate:
            muted_notes = files.enter_context(open_private(notes.with_suffix(".muted.jsonl")))
        while not table.game.winner:
            now = table.opens
            muted = {}
            if debate and table.game.stage == "eliminate_vote":
                # Identical electorate and decision before and after the actual public utterance.
                before = table.view(nominator, now - table.discussion)
                statement = advocate(before, model)
                if statement:
                    quiet_table = deepcopy(table)
                    muted = {
                        s: quiet_table.view(s, now)
                        for s in before["state"]["alive"]
                        if s != nominator
                    }
                    table.say(nominator, table.revision, statement, now - table.discussion)
            snapshots = [table.view(s, now) for s in seats]
            for snap in snapshots:
                if not (choices := snap["choices"]):
                    continue
                seat, state = snap["seat"], snap["state"]
                stage = state["stage"]
                if (seat == 0 or debate) and stage in ("nominate", "eliminate_vote"):
                    snap["table_id"] = table.record["table_id"]
                    choice = elimination(snap, sink)
                    comparison = None
                    if seat in muted:
                        comparison = elimination(muted[seat], muted_notes)["vote"]
                    calls.append(
                        dict(
                            seed=seed,
                            bad=bad,
                            **({"seat": seat, "muted_vote": comparison} if debate else {}),
                            turn=state["turn"],
                            event=snap["revision"] + 1,
                            stage=stage,
                            pending=state["pending"],
                            choice=next(iter(choice.values())),
                        )
                    )
                elif model_floor:
                    snap["table_id"] = table.record["table_id"]
                    choice = infer(
                        snap,
                        model,
                        30,
                        guided=True,
                        social_guidance=social_guidance,
                        outcome_policy=outcome_policy,
                        named_moves=True,
                        named_ballots=True,
                        no_think=True,
                        note_file=sink,
                    )
                elif stage == "place":
                    # The drawing seat knows whether it must return a tile. Read its draw receipt.
                    state["draw_count"] = int(snap["history"][-1]["text"].split()[2])
                    menu = plans(state, choices)
                    best = min(map(score, menu))
                    plan = pick.choice([p for p in menu if score(p) == best])
                    destination = plan["to"]
                    choice = plan["place"]
                elif stage == "propose":
                    delay = state["role"] == "bad" and state["turn"] >= 3
                    choice = {"to": None if delay else destination}
                elif stage == "discard":
                    choice = {"tile": min(choices["tile"], key=lambda f: (f.bit_count(), f))}
                elif stage == "move_vote":
                    choice = {"vote": approach(state) == (state["role"] == "good")}
                elif stage == "nominate":
                    other = 3 - seat
                    choice = {
                        "target": other if state["turn"] == 2 and other in state["alive"] else None
                    }
                elif stage == "eliminate_vote":
                    # Each script backs removal of the other scripted seat, never itself.
                    choice = {"vote": state["pending"] == 3 - seat}
                else:
                    raise AssertionError(stage)
                if stage == "nominate" and choice["target"] is not None:
                    nominator = seat
                table.submit(seat, snap["revision"], choice, now)
    assert replay(table.record).winner == table.game.winner
    output.write_text(json.dumps(table.record, separators=(",", ":")) + "\n")
    print(
        f"{seed=} P{bad} bad: {table.game.winner} turn {table.game.turn}, {len(calls)} model choices",
        flush=True,
    )
    return calls


def write_rows(path, rows):
    with path.open("x", newline="") as f:
        w = csv.DictWriter(f, rows[0], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--arm", choices=("base", "focused", "ledger", "receipt"), default="base")
    parser.add_argument(
        "--debate",
        action="store_true",
        help="all seats model nominations and elimination votes; nominator may speak",
    )
    parser.add_argument(
        "--bad-brief",
        action="store_true",
        help="spell out what the sole bad seat knows on its elimination decisions",
    )
    parser.add_argument(
        "--model-floor",
        action="store_true",
        help="in debate games, use the guided Ollama seat for all construction and movement decisions too",
    )
    parser.add_argument(
        "--social-guidance",
        action="store_true",
        help="use the experimental seat-relative payoff prompt",
    )
    parser.add_argument(
        "--outcome-policy",
        action="store_true",
        help="use the hybrid seat policy for social decisions",
    )
    parser.add_argument("--roles", help="one explicit role layout for full model play, e.g. GBGB")
    parser.add_argument("--kit-counts", type=int, nargs=2, metavar=("IN", "OUT"))
    parser.add_argument("--kit-seed", type=int, help="fixed-count mix seed (default: 0)")
    parser.add_argument("--seeds", type=int, nargs="+", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--private-notes", type=Path, required=True)
    args = parser.parse_args()
    if (
        args.model_floor or args.bad_brief or args.social_guidance or args.outcome_policy
    ) and not args.debate:
        parser.error(
            "--model-floor, --bad-brief, --social-guidance and --outcome-policy require --debate"
        )
    layouts = (["good", "bad", "good"], ["good", "good", "bad"])
    if args.roles is not None:
        if not (
            args.model_floor
            and args.debate
            and len(args.roles) in (3, 4)
            and set(args.roles) == {"G", "B"}
        ):
            parser.error("--roles requires full model play and 3 or 4 seats with both G and B")
        layouts = (["good" if c == "G" else "bad" for c in args.roles],)
    if args.kit_seed is not None and args.kit_counts is None:
        parser.error("--kit-seed requires --kit-counts")
    kit = PAPER_KIT
    if args.kit_counts is not None:
        try:
            kit = fixed_kit(Random(args.kit_seed or 0), 16, *args.kit_counts)
        except ValueError as err:
            parser.error(str(err))
    args.out.mkdir(parents=True, exist_ok=False)
    args.private_notes.mkdir(mode=0o700, parents=True, exist_ok=False)
    request(
        11434,
        "/api/generate",
        {"model": args.model, "stream": False, "options": {"num_ctx": 4096}},
        180,
    )
    rows = []
    for seed in args.seeds:
        for roles in layouts:
            bad = "+".join(str(s) for s, role in enumerate(roles) if role == "bad")
            name = f"{seed}-bad{bad}"
            rows.extend(
                social_game(
                    seed,
                    roles,
                    args.model,
                    args.out / f"{name}.json",
                    args.private_notes / f"{name}.jsonl",
                    args.arm,
                    args.debate,
                    args.bad_brief,
                    args.model_floor,
                    args.social_guidance,
                    args.outcome_policy,
                    kit=kit,
                )
            )
    write_rows(args.out / "choices.csv", rows)


if __name__ == "__main__":
    main()
