"""Report paired cooperative outcomes and actual requests on the rotation panel."""

import argparse
import csv
import sys
from ast import literal_eval
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

from experiments.archive_rows import csv_rows
from experiments.rotation_probe import cases, success
from footsteps.decision_notes import read_notes
from footsteps.record import read
from footsteps.viewer import transcript


def summary(root):
    groups = defaultdict(dict)
    for r in read_csv(root / "cooperative/deals.csv"):
        groups[r["kit"], r["policy"]].setdefault(r["seed"], {})[r["arm"]] = r
    for name, pairs in groups.items():
        transitions = Counter(
            (int(d["rotate"]["win"]), int(d["fixed"]["win"])) for d in pairs.values()
        )
        print(*name, "wins (rotate, fixed)", dict(sorted(transitions.items())))
        for arm in ("rotate", "fixed"):
            rs = [d[arm] for d in pairs.values()]
            print(
                arm,
                "wins",
                sum(int(r["win"]) for r in rs),
                "/",
                len(rs),
                "misses / turns needing a build",
                sum(int(r["no_forward_build"]) for r in rs),
                "/",
                sum(int(r["needed"]) for r in rs),
            )
    positions = {name: snap for name, snap, _, turns in cases() if turns is None}
    for encoding in ("decisions", "named"):
        groups = defaultdict(list)
        for r in read_csv(root / f"{encoding}.csv"):
            groups["ports" if r["case"].startswith("ports-") else "social", r["arm"]].append(r)
        for name, rs in groups.items():
            offered = Counter(r["lookup"] for r in rs if r["lookup"])
            picked = sum(
                r["requested_face"] == r["picked_face"] for r in rs if r["lookup"] == "answered"
            )
            print(
                encoding,
                *name,
                "correct / feasible / total",
                sum(int(r["success"]) for r in rs),
                sum(int(r["viable"]) > 0 for r in rs),
                len(rs),
                "by menu order",
                [
                    (o, sum(int(r["success"]) for r in rs if r["reverse"] == o))
                    for o in ("False", "True")
                ],
                "lookup",
                dict(offered),
                "built requested face",
                picked,
                "median tokens in/out",
                *(
                    median(int(r[key]) for r in rs if r[key])
                    for key in ("prompt_tokens", "output_tokens")
                ),
                "median seconds",
                round(median(float(r["seconds"]) for r in rs), 2),
            )
            if name[0] == "social":
                rescued = square = 0
                for row in rs:
                    if row["status"] != "accepted":
                        continue
                    snap = positions[row["case"]]
                    at = literal_eval(row["at"])

                    viable_faces = {
                        f
                        for f in snap["choices"]["tile"]
                        if any(success(snap["state"], f, r, at, None) for r in range(4))
                    }
                    rescued += int(row["picked_face"]) in viable_faces
                    square += bool(viable_faces)
                print(
                    "chosen square works with chosen face / any held face at any rotation:",
                    rescued,
                    square,
                )


def social_receipts(record_path, note_path):
    record = read(record_path)
    frames = transcript(record, omniscient=True, notes=read_notes([note_path]))["frames"]
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(
        ["turn", "event", "seat", "status", "requested_face", "placed_face", "rotation", "timeout"]
    )
    for i, event in enumerate(record["events"], 1):
        if event["kind"] != "place":
            continue
        frame = frames[i]
        seat = frames[i - 1]["actor"]
        notes = frame.get("decision_notes", [])
        tools = notes[0].get("tools", []) if notes else []
        receipt = next((t for t in tools if t["name"] == "inspect_rotations"), {})
        writer.writerow(
            [
                frame["event_turn"],
                i,
                seat,
                receipt.get("status", "unobserved"),
                receipt.get("tile"),
                event["tile"],
                event["rotation"],
                event.get("timeout", False),
            ]
        )


def read_csv(path):
    with path.open() as f:
        return list(csv_rows(f))


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("root", type=Path)
    cli.add_argument(
        "--social-notes",
        type=Path,
        help="export postgame placement receipts for the matched 8602 game as CSV",
    )
    args = cli.parse_args()
    if args.social_notes:
        social_receipts(args.root / "social/8602-red1+3.json", args.social_notes)
    else:
        summary(args.root)
