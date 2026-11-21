"""Generate private predeal strategy notes and test them on post-compaction ballots."""

import argparse
import hashlib
import json
from functools import partial
from pathlib import Path

from experiments.horizon_votes import ballot_facts, fixture, seat_session
from experiments.persistent_runtime import resident_model
from experiments.rana_speakers import act
from footsteps.decision_notes import open_private
from footsteps.ollama import request
from footsteps.session import MOVEMENT_CLOCK, Session

MODELS = {"27b": "footsteps-qwen3.8:27b-rana-layout", "9b": "qwen3.5:9b-q8_0"}
CONTEXT = 8192
ORIGINAL_SYSTEM = (
    (Path(__file__).parent / "pregame-analysis/original-system.txt").read_text().rstrip("\n")
)
# Procedural rules only. The full human rulebook explicitly derives the target bound.
RULES = """Footsteps is played on an unbounded square grid. East increases x and north increases y. EXIT is at (0,0). START and EXIT have open entrances and exits on all four sides. The shared marker starts at START. There are three Blue seats and one Red seat. Blue wins when the marker enters EXIT. Red wins if a movement opportunity ends short of EXIT with the store empty, or all Blue seats are eliminated. Eliminated players share the result of their team. A Blue player knows only their own role. A Red player knows the Red roster. These information rules and the starting team counts are public.

Players start with two private tiles each. The other tiles form the store. The living builders take turns. Draw two tiles, or the remaining one if only one is left. Choose a tile from your hand and place it with any rotation at an empty square edge-adjacent to START or an ordinary tile. Placed tiles remain fixed. If you drew two, return one remaining tile from your hand to the store. If you drew one, skip the return.

The builder proposes staying or taking one step to an edge-adjacent tile. A step requires an exit on the source and an entrance on the facing side of the destination. Building does not move the marker. Living players vote on a proposed step. A majority Yes moves it, and a tie follows the builder's own vote. Otherwise it stays. Check EXIT before exhaustion. If play continues, each living seat may nominate another for removal. A strict majority is needed to remove the nominee. All players hear public remarks before voting, and either team may bluff."""
TASK = "Before roles are dealt, write yourself a private strategy note of 100–200 words for playing either team. Your note will be restored after later context compactions. Give only the finished note."
CUES = {
    "open": "",
    "invariants": " Look for invariants in the rules and the environment that let you judge whether a position is still winnable or already unwinnable.",
}


def digest(note):
    return hashlib.sha256(note.encode()).hexdigest()


def write_note(model, cue, seed, owner, log):
    thinking = cue == "deliberate"
    hint = CUES["invariants" if thinking or cue == "clarified-invariants" else cue]
    messages = [
        {
            "role": "system",
            "content": RULES + (" " + MOVEMENT_CLOCK if cue == "clarified-invariants" else ""),
        },
        {"role": "user", "content": TASK + hint},
    ]
    options = {"num_ctx": CONTEXT, "temperature": 0.7, "seed": seed}
    limits = (3072, 6144) if thinking else (512, 1024)
    attempts = []
    for limit in limits:
        response = request(
            11434,
            "/api/chat",
            {
                "model": model,
                "stream": False,
                "think": thinking,
                "messages": messages,
                "options": options | {"num_predict": limit},
            },
            480 if thinking else 120,
        )
        attempts.append(limit)
        note = response["message"]["content"].strip()
        if note and response.get("done_reason") != "length":
            break
    else:
        raise ValueError(f"Incomplete note for {model} {cue} {seed} after {attempts}")
    key = {"model": model, "cue": cue, "seed": seed, "sha256": digest(note)}
    print(json.dumps(key | {"note": note}), file=owner, flush=True)
    print(
        json.dumps(
            key
            | {
                "words": len(note.split()),
                "tokens": response.get("eval_count"),
                "attempt_limits": attempts,
            }
        ),
        file=log,
        flush=True,
    )


def generate(model, owner, log, deliberate=False):
    for seed in (1, 2, 3):
        for cue in ("deliberate",) if deliberate else CUES:
            write_note(model, cue, seed, owner, log)


class PreparedSession(Session):
    """Restore the seat's unedited predeal note separately from its rolling summary."""

    def __init__(self, *args, pregame_note, clarified=False, **kwargs):
        self.clarified = clarified
        self.pregame_note = pregame_note
        super().__init__(*args, **kwargs)

    def reset(self, *, recovered=False):
        super().reset(recovered=recovered)
        if not self.clarified:
            self.messages[0]["content"] = ORIGINAL_SYSTEM
        if self.pregame_note:
            bootstrap = self.messages[-1]
            private = json.loads(bootstrap["content"])
            private["your_private_pregame_note"] = self.pregame_note
            bootstrap["content"] = json.dumps(private)


def ballot(model, note, case, heading, team, *, clarified=False):
    s = seat_session(
        fixture(case, heading),
        3,
        team,
        session_class=partial(PreparedSession, pregame_note=note, clarified=clarified),
        context=CONTEXT,
    )
    rev = s.snap["revision"]
    # Exercise the normal tool handler. The same scripted rolling summary is
    # used in every arm; no historic conversation or answer key is retained.
    s.execute("compact", {"summary": "A movement ballot is open."}, s.tools(), rev)
    bootstrap = json.loads(s.messages[-1]["content"])
    assert bootstrap.get("your_private_pregame_note", "") == note
    calls = act(s, model, False)
    t = s.seat.table
    vote = t.votes.get(3) if t.revision == rev else None
    facts = ballot_facts(s.messages, model=model, context=CONTEXT) if vote is not None else {}
    return {
        "case": case,
        "heading": heading,
        "team": team,
        "vote": vote,
        "facts": facts,
        "calls": calls,
    }


def read_notes(model, owner_path, expected):
    notes = [json.loads(line) for line in owner_path.read_text().splitlines()]
    if len(notes) != len(expected) or {(r["cue"], r["seed"]) for r in notes} != expected:
        raise ValueError("the private note panel is incomplete or duplicated")
    if any(r["model"] != model or digest(r["note"]) != r["sha256"] for r in notes):
        raise ValueError("expected intact notes from the model being evaluated")
    return notes


def transfer(model, notes, out, *, include_control=True, clarified=False):
    control = {
        "cue": "clarified-none" if clarified else "none",
        "seed": None,
        "sha256": None,
        "note": "",
    }
    conditions = [control, *notes] if include_control else notes
    for row in conditions:
        key = {"model": model, **{k: row[k] for k in ("cue", "seed", "sha256")}}
        for case in ("short", "detour"):
            for heading in ("west", "north"):
                for team in ("blue", "red"):
                    result = ballot(model, row["note"], case, heading, team, clarified=clarified)
                    print(json.dumps(key | result), file=out, flush=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("phase", choices=("generate", "transfer"))
    cli.add_argument("model", choices=MODELS)
    cli.add_argument("private", type=Path)
    cli.add_argument("output", type=Path)
    arms = cli.add_mutually_exclusive_group()
    arms.add_argument(
        "--clarified",
        action="store_true",
        help="use the revised public clock rules in preparation and play; compare seed one against a matched bare seat",
    )
    arms.add_argument(
        "--deliberate",
        action="store_true",
        help="invariant cue with thinking enabled at note-writing time only; reuse the existing no-note ballot results",
    )
    args = cli.parse_args()
    model = MODELS[args.model]
    cues = ("deliberate",) if args.deliberate else CUES
    seeds = (1, 2, 3)
    if args.clarified:
        cues, seeds = ("clarified-invariants",), (1,)
    if args.phase == "transfer":
        expected = {(cue, seed) for seed in seeds for cue in cues}
        notes = read_notes(model, args.private, expected)
    with args.output.open("x") as log:
        if args.phase == "generate":
            with open_private(args.private) as owner:
                generate(model, owner, log, seeds, cues)
        else:
            transfer(
                model, notes, log, include_control=not args.deliberate, clarified=args.clarified
            )
    print(json.dumps(resident_model(model)))
