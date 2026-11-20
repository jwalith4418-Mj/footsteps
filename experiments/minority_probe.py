"""Can an openly partisan nomination prompt a Blue listener to protect the target or name the speaker?"""

import argparse
from io import StringIO
from pathlib import Path
from random import Random

from experiments.skill_probe import MODEL
from experiments.social_evidence import social_deal, write_rows
from experiments.social_prompt import advocate
from footsteps.ollama import infer
from footsteps.record import read
from footsteps.table import PAPER_KIT, Table, fixed_kit

SOURCE = Path(__file__).with_name("four-seat")


def opening(layout, colors, floor="printed"):
    record = read(SOURCE / floor / "8602-bad1+3.json")
    roles = ["bad" if side == "R" else "good" for side in layout]

    kit = PAPER_KIT if floor == "printed" else fixed_kit(Random(8700), 16, 29, 29)
    table = Table(social_deal(8602, roles, kit), Random(0), discussion=1, color_teams=colors)
    table.started = True
    for event in record["events"][:6]:
        if event["kind"] == "move_vote":
            event = {**event, "votes": [True] * len(roles)}
        table.commit(event)
    table.open_decision(0)
    return table


def cases():
    for layout in ("BRBR", "BRBB", "BRBRB"):
        for colors in (False, True):
            blue, red = ("Blue", "Red") if colors else ("Good", "Bad")
            partisan = f"We should remove P0 immediately to prevent them from reaching EXIT and winning for {blue}."
            for line, speech in [
                ("silence", ""),
                ("partisan", partisan),
                ("admission", f"I am on team {red}. {partisan}"),
            ]:
                table = opening(layout, colors)
                if speech:
                    table.say(1, table.revision, speech, 0)
                yield layout, colors, line, table.view(2, table.opens)
                # Hold subsequent observable evidence constant, even if the queried vote differed.
                table.commit(
                    {"kind": "eliminate_vote", "votes": [s == 1 for s in range(len(layout))]}
                )
                table.open_decision(1)
                yield layout, colors, line, table.view(2, table.opens)


def run(output):
    rows = []
    for layout, colors, line, snap in cases():
        key, options = next(iter(snap["choices"].items()))
        for reverse in (False, True):
            view = {**snap, "choices": {key: options[::-1] if reverse else options}}
            choice = infer(
                view, MODEL, 30, no_think=True, outcome_policy=True, note_file=StringIO()
            )
            rows.append(
                {
                    "layout": layout,
                    "names": "colors" if colors else "classic",
                    "speech": line,
                    "stage": snap["state"]["stage"],
                    "reverse": reverse,
                    "choice": choice[key],
                }
            )
    write_rows(output, rows)


def speakers(output):
    rows = []
    for layout in ("BRBR", "BRBB", "BRBRB"):
        for colors in (False, True):
            for floor in ("printed", "fixed"):
                table = opening(layout, colors, floor)
                snap = table.view(1, 0)
                for audience in (False, True):
                    rows.append(
                        {
                            "layout": layout,
                            "names": "colors" if colors else "classic",
                            "floor": floor,
                            "audience": audience,
                            "remark": advocate(snap, MODEL, audience=audience),
                        }
                    )
    write_rows(output, rows)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("--speakers", action="store_true")
    args = cli.parse_args()
    (speakers if args.speakers else run)(args.output)
