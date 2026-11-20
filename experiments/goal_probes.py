"""Re-present directed detours and paired social builds with the frozen floor interface."""

import argparse
import json
from io import StringIO
from itertools import product
from pathlib import Path
from random import Random

from experiments.action_probe import position
from experiments.goal_pursuit import decide
from experiments.native_transfer import transfer_panel
from experiments.plan_tactics import detour_table, viable
from experiments.rotation_probe import success
from experiments.skill_probe import MODEL


class Order(Random):
    def __init__(self, seed, reverse):
        super().__init__(seed)
        self.reverse = reverse

    def shuffle(self, xs):
        super().shuffle(xs)
        if self.reverse:
            xs.reverse()


def detours(model, arm):
    for sx, sy, rev in product((-1, 1), (-1, 1), (False, True)):
        table = detour_table(sx, sy)
        snap = table.view(0, 0)
        calls = []
        order = Order(f"detour/{sx}/{sy}", rev)
        row = {"case": [sx, sy], "reverse": rev, "calls": calls, "success": False}
        try:
            build = decide(snap, model, None, calls, arm=arm, order=order)
            table.submit(0, table.revision, build, 0)
            table.submit(0, table.revision, {"tile": 0}, 0)
            step = decide(table.view(0, 0), model, None, calls, arm=arm, order=order)
            table.submit(0, table.revision, step, 0)
            row.update(
                build=build, step=step, success=viable(snap["state"], {"place": build, **step})
            )
        except (ValueError, OSError) as exc:
            row["error"] = str(exc)
        yield row


def social(model, arm, max_reply=140):
    for start_seed in (9600, 9700):
        for idx, (name, snap, _, _) in enumerate(transfer_panel(start_seed=start_seed)):
            log = []
            row = {"case": name, "calls": log, "success": False}
            try:
                note = StringIO()
                a = decide(
                    snap,
                    model,
                    note,
                    log,
                    arm=arm,
                    order=Random(f"paired/{idx // 2}"),
                    max_reply=max_reply,
                )
                row["private_reason"] = json.loads(note.getvalue())["reason"]
                row.update(
                    choice=a,
                    success=success(snap["state"], a["tile"], a["rotation"], tuple(a["at"]), None),
                )
            except (ValueError, OSError) as exc:
                row["error"] = str(exc)
            yield row


def ballots(model, arm):
    source = Path(__file__).with_name("native-actions") / "games" / "9501-hand-all.json"
    record = json.loads(source.read_text())
    for revision in (4, 15, 25):
        event = record["events"][revision]
        assert event["kind"] == "move_vote"
        for seat, previous in enumerate(event["votes"]):
            snap = position(source, revision, seat)
            log = []
            row = {
                "event": revision + 1,
                "case": f"ballot-{revision + 1}-P{seat}",
                "seat": seat,
                "previous": previous,
                "role": snap["state"]["role"],
                "calls": log,
            }
            try:
                row["vote"] = decide(
                    snap, model, None, log, arm=arm, order=Random(f"ballot/{revision}")
                )["vote"]
            except (ValueError, OSError) as exc:
                row["error"] = str(exc)
            yield row


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("panel", choices=("detours", "social", "ballots"))
    p.add_argument("output", type=Path)
    p.add_argument("--model", default=MODEL)
    p.add_argument("--arm", choices=("forecast", "brief", "personal", "last"), default="forecast")
    p.add_argument("--max-reply", type=int, choices=(140, 320), default=140)
    args = p.parse_args()
    with args.output.open("x") as out:
        trials = (
            social(args.model, args.arm, args.max_reply)
            if args.panel == "social"
            else {"detours": detours, "ballots": ballots}[args.panel](args.model, args.arm)
        )
        for row in trials:
            out.write(json.dumps(row, separators=(",", ":")) + "\n")
            out.flush()
