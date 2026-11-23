"""Compare two forecast wordings on identical fresh private snapshots, without casting a ballot."""

import argparse
import json
from pathlib import Path

from experiments.exit_interest import CONTEXT, FIELDS, FORECAST, MODELS, conditions, prefix, seat
from experiments.horizon_votes import question
from footsteps.record import replay

OUTCOMES = (
    "lands_on_exit_now",
    "play_continues_exit_is_reachable",
    "play_continues_exit_is_unreachable",
    "game_ends_short_of_exit",
)


def panel(model):
    for case in ("13401", "trap"):
        builder = replay(prefix(case)).actor
        for voter, roles in conditions(case):
            if voter == builder or roles[builder] != "blue":
                continue
            session = seat(case, voter, roles)
            team = roles[voter]
            # Counterbalance listing order across the two seat interests. Both forks
            # see exactly the same initial private board, with no vote or answer.
            labels = OUTCOMES if team == "blue" else OUTCOMES[::-1]
            messages = session.messages
            original = question(messages, FORECAST, FIELDS, model=model, context=CONTEXT)
            plain = question(
                messages,
                "Suppose the table approves the pending step. Choose one outcome: "
                + ", ".join(labels)
                + ". Reachability includes any legal future play. Which team benefits from approval (blue or red)?",
                {"outcome": "string", "beneficiary": "string"},
                model=model,
                context=CONTEXT,
            )
            yield {
                "model": model,
                "case": case,
                "team": team,
                "voter": voter,
                "original": original,
                "outcome_and_beneficiary": plain,
            }


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("model", choices=MODELS)
    cli.add_argument("output", type=Path)
    args = cli.parse_args()
    with args.output.open("x") as out:
        for row in panel(MODELS[args.model]):
            print(json.dumps(row), file=out, flush=True)
