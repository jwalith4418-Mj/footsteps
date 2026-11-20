"""Rebuild archived candidate menus and verify the executed turn against the selected plan."""

import argparse
import json
from functools import partial
from pathlib import Path
from random import Random

from experiments.turn_plans import plans
from footsteps.record import read
from footsteps.table import Table


def audit_game(path, make_plans=plans):
    seed = int(path.stem.split("-")[1])
    logged = iter(
        json.loads(line) for line in (path.parent / f"plans-{seed}.jsonl").read_text().splitlines()
    )
    record = read(path)
    table = Table(record["setup"], Random(0))
    table.started = True
    order = Random(f"plan-order/{seed}")
    selected = None
    count = 0
    for e in record["events"]:
        stage = e["kind"]
        if stage == "place":
            state = table.game.view(0)
            state["draw_count"] = len(table.record["events"][-1]["tiles"])
            menu = make_plans(state, table.choices(0, 0))
            order.shuffle(menu)
            selected = None
            if not e.get("timeout"):
                row = next(logged)
                if row["turn"] != table.game.turn or json.loads(json.dumps(menu)) != row["menu"]:
                    raise ValueError(f"{path}: offered menu differs on turn {table.game.turn}")
                pick = row["pick"]
                if type(pick) is not int or not 0 <= pick < len(menu):
                    raise ValueError(f"{path}: bad selection index")
                selected = menu[pick]
                if selected["place"] != {k: e[k] for k in ("at", "tile", "rotation")}:
                    raise ValueError(f"{path}: build does not match plan")
                count += 1
        if stage == "discard" and e["tile"] != min(
            table.game.hands[0], key=lambda f: (f.bit_count(), f)
        ):
            raise ValueError(f"{path}: discard differs")
        if stage == "propose":
            dest = None if e["to"] is None else tuple(e["to"])
            if (selected is None and not e.get("timeout")) or (
                selected is not None and selected["to"] != dest
            ):
                raise ValueError(f"{path}: walk does not match plan")
        table.commit(e)
    if next(logged, None) is not None or not table.game.winner:
        raise ValueError(f"{path}: surplus plans or incomplete game")
    return count


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("folders", type=Path, nargs="+")
    cli.add_argument("--local", action="store_true")
    args = cli.parse_args()
    for folder in args.folders:
        print(
            folder.name,
            sum(
                audit_game(p, partial(plans, local=args.local))
                for p in sorted(folder.glob("game-*.json"))
            ),
            "complete plans checked",
        )
