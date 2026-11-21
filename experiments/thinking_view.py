"""Join owner-only Ollama traces to verified ballot receipts and export the frozen floors."""

import argparse
import hashlib
import html
import json
from collections import defaultdict
from pathlib import Path

from experiments.ballot_thinking import TRANSFER, position
from footsteps.decision_notes import save_private_export
from footsteps.viewer import export_html

ROOT = Path(__file__).parent / "ballot-thinking"


def key(row):
    return tuple(row[k] for k in ("model", "budget", "case", "seat", "team", "revision"))


def build(receipts, owner, output):
    output.mkdir(mode=0o700, exist_ok=True)
    notes = defaultdict(list)
    seen = set()
    panels = defaultdict(list)
    for path in sorted(receipts.glob("*.jsonl")):
        private = {}
        for line in (owner / path.name).read_text().splitlines():
            row = json.loads(line)
            k = key(row), row["index"]
            if k in private:
                raise ValueError("duplicate private call")
            private[k] = row
        for line in path.read_text().splitlines():
            row = json.loads(line)
            k = key(row)
            if k in seen:
                raise ValueError("duplicate public decision")
            seen.add(k)
            floor = (row["case"], row["team"])
            panels[
                "Directed route" if row["case"] in TRANSFER else "EXIT / dead end",
                row["model"],
                row["budget"],
            ].append(row)
            vote = {True: "Yes", False: "No", None: "no submission"}[row["vote"]]
            for c in row["calls"]:
                entry = private.pop((k, c["index"]))
                trace = entry["thinking"]
                digest = hashlib.sha256(trace.encode()).hexdigest() if trace else None
                if digest != c["thinking_sha256"] or len(trace) != c["thinking_chars"]:
                    raise ValueError("thinking text differs from the public receipt")
                if not row["budget"]:
                    continue
                label = (
                    f"{row['budget']} budget · ballot {vote} · call {c['index'] + 1} · "
                    f"{c['tokens']} tokens · {c['seconds']:.1f}s · {c['done_reason']} · {c['tool'] or 'no tool'}"
                )
                notes[floor].append(
                    {
                        "kind": "thinking",
                        "version": 1,
                        "table_id": "study-" + "-".join(floor),
                        "revision": row["revision"],
                        "turn": row["turn"],
                        "stage": "move_vote",
                        "seat": row["seat"],
                        "model": row["model"],
                        "label": label,
                        "thinking": trace,
                    }
                )
        if private:
            raise ValueError("private calls have no public receipt")
    links = []
    for (case, team), traces in sorted(notes.items()):
        record, _ = position(case, team)
        record["table_id"] = traces[0]["table_id"]
        filename = f"{case}-{team}.html"
        label = {
            "13401": "EXIT",
            "trap": "Dead end",
            "short": "Short outward step",
            "detour": "Necessary detour",
        }[case]
        title = f"{label} · {team.title()} voter"
        save_private_export(
            output / filename, export_html(record, title, omniscient=True, notes=traces)
        )
        links.append(
            f'<li><a href="{filename}#event={len(record["events"])}">{html.escape(title)}</a></li>'
        )
    table = []
    for (panel, model, budget), rows in sorted(panels.items()):
        calls = [c for r in rows for c in r["calls"]]
        table.append(
            f"<tr><td>{html.escape(panel)}</td><td>{html.escape(model)}</td><td>{budget or 'Off'}</td><td>{sum(r['vote'] is not None for r in rows)}/{len(rows)}</td>"
            f"<td>{sum(r['aligned'] for r in rows)}/{len(rows)}</td><td>{sum(c['tokens'] for c in calls)}</td>"
            f"<td>{sum(c['seconds'] for c in calls) / len(rows):.1f}</td></tr>"
        )
    save_private_export(
        output / "index.html",
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Footsteps · Private ballot trials</title><style>body{font:1.05rem system-ui;line-height:1.5;max-width:64rem;margin:3rem auto;padding:0 1rem;color:#273432}table{border-collapse:collapse}td,th{text-align:left;padding:.45rem .7rem;border-bottom:1px solid #ccc}a{color:#156456}</style>
<h1>Private ballot trials</h1><p>Open a board to inspect the proposed step. Expand a call in the event log to read the text Ollama returned before its tool choice or output limit. The trials are alternative decisions on the same position.</p><ul>"""
        + "".join(links)
        + "</ul><table><thead><tr><th>Boards</th><th>Model</th><th>Token allowance</th><th>Submitted</th><th>Team-serving</th><th>Generated tokens</th><th>Seconds/decision</th></tr></thead><tbody>"
        + "".join(table)
        + "</tbody></table></html>",
    )


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument(
        "owner",
        type=Path,
        help="directory of private call files with the same names as the public receipts",
    )
    cli.add_argument("output", type=Path)
    cli.add_argument("--receipts", type=Path, default=ROOT)
    args = cli.parse_args()
    build(args.receipts, args.owner, args.output)
