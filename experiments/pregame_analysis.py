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
ROUTE_BOUND = (
    "From each possible ballot landing, the marker needs at least "
    "|x - exit_x| + |y - exit_y| more steps. If that distance exceeds the remaining "
    "movement opportunities, Blue cannot reach EXIT. Fitting inside this budget is "
    "only a necessary condition. A legal directed route may first lead away from EXIT."
)
CLOCK_SYSTEM = ORIGINAL_SYSTEM.replace("North increases y.", "North increases y. " + MOVEMENT_CLOCK)
PROMPTS = {
    "none": ORIGINAL_SYSTEM,
    "clarified-none": CLOCK_SYSTEM,
    "taught-none": CLOCK_SYSTEM + " " + ROUTE_BOUND,
}
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


def draft_reply(model, messages, options, *, thinking, limit, timeout):
    return request(
        11434,
        "/api/chat",
        {
            "model": model,
            "stream": False,
            "think": thinking,
            "messages": messages,
            "options": options | {"num_predict": limit},
        },
        timeout,
    )


def finish_draft(model, messages, options, draft):
    return draft_reply(
        model,
        [
            *messages,
            {"role": "assistant", "content": draft},
            {
                "role": "user",
                "content": "Finish your private pregame note now. Give only the 100–200 word note you want restored during play.",
            },
        ],
        options,
        thinking=False,
        limit=1024,
        timeout=180,
    )


def write_note(model, cue, seed, owner, log):
    extended_context = {
        "deliberate-16k": 16384,
        "deliberate-32k": 32768,
        "finish-draft": 16384,
    }.get(cue)
    thinking = cue == "deliberate" or extended_context is not None
    hint = CUES["invariants" if thinking or cue == "clarified-invariants" else cue]
    messages = [
        {
            "role": "system",
            "content": RULES + (" " + MOVEMENT_CLOCK if cue == "clarified-invariants" else ""),
        },
        {"role": "user", "content": TASK + hint},
    ]
    options = {"num_ctx": extended_context or CONTEXT, "temperature": 0.7, "seed": seed}
    limits = (512, 1024)
    if cue == "finish-draft":
        limits = (3072,)
    elif extended_context:
        limits = (extended_context - 2048,)
    elif thinking:
        limits = (3072, 6144) if seed == 1 else (3072,)
    attempts = []
    usage = {}
    for limit in limits:
        response = draft_reply(
            model,
            messages,
            options,
            thinking=thinking,
            limit=limit,
            timeout=2400 if extended_context else (480 if thinking else 120),
        )
        if extended_context:
            usage = {
                "preparation_context": extended_context,
                "prompt_tokens": response.get("prompt_eval_count"),
                "generated_tokens": response.get("eval_count"),
                "seconds": round(response.get("total_duration", 0) / 1e9, 2),
                "done_reason": response.get("done_reason"),
            }
        attempts.append(limit)
        if cue == "finish-draft" and response.get("done_reason") == "length":
            # The model's intermediate work stays in memory until its own writing pass ends.
            # No raw draft enters the owner's memo file, referee data or playing context.
            draft = "\n".join(
                part
                for field in ("thinking", "content")
                if (part := response["message"].get(field))
            )
            if draft:
                response = finish_draft(model, messages, options, draft)
                usage["writing_tokens"] = response.get("eval_count")
                usage["writing_seconds"] = round(response.get("total_duration", 0) / 1e9, 2)
                usage["writing_done_reason"] = response.get("done_reason")
                attempts.append(1024)
        note = response["message"]["content"].strip()
        if note and response.get("done_reason") != "length":
            break
    else:
        failed = {"model": model, "cue": cue, "seed": seed, "sha256": None, "status": "unfinished"}
        print(json.dumps(failed | {"note": None}), file=owner, flush=True)
        print(json.dumps(failed | {"attempt_limits": attempts} | usage), file=log, flush=True)
        return
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
            | usage
        ),
        file=log,
        flush=True,
    )


def generate(model, owner, log, seeds, cues):
    for seed in seeds:
        for cue in cues:
            write_note(model, cue, seed, owner, log)


class PreparedSession(Session):
    """Restore the seat's unedited predeal note separately from its rolling summary."""

    def __init__(self, *args, pregame_note, system_prompt=ORIGINAL_SYSTEM, **kwargs):
        self.system_prompt = system_prompt
        self.pregame_note = pregame_note
        super().__init__(*args, **kwargs)

    def reset(self, *, recovered=False):
        super().reset(recovered=recovered)
        self.messages[0]["content"] = self.system_prompt
        if self.pregame_note:
            bootstrap = self.messages[-1]
            private = json.loads(bootstrap["content"])
            private["your_private_pregame_note"] = self.pregame_note
            bootstrap["content"] = json.dumps(private)


def ballot(model, note, case, heading, team, *, system_prompt):
    s = seat_session(
        fixture(case, heading),
        3,
        team,
        session_class=partial(PreparedSession, pregame_note=note, system_prompt=system_prompt),
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
    complete = [r for r in notes if r.get("status") != "unfinished"]
    if any(r["model"] != model for r in notes) or any(
        digest(r["note"]) != r["sha256"] for r in complete
    ):
        raise ValueError("expected intact notes from the model being evaluated")
    return complete


def transfer(model, notes, out, *, include_control=True, control_cue="none"):
    control = {
        "cue": control_cue,
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
                    result = ballot(
                        model, row["note"], case, heading, team, system_prompt=PROMPTS[control_cue]
                    )
                    print(json.dumps(key | result), file=out, flush=True)


def main(argv=None):
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("phase", choices=("generate", "transfer", "teach"))
    cli.add_argument("model", choices=MODELS)
    cli.add_argument(
        "private", type=Path, nargs="?", help="owner note file for generate or transfer"
    )
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
    arms.add_argument(
        "--preparation-context",
        type=int,
        choices=(16384, 32768),
        help="retry invariant preparation with thinking on, seed 1, reserving 2048 tokens for input. Ballots still use 8192",
    )
    arms.add_argument(
        "--finish-draft",
        action="store_true",
        help="use a 16k context and ask the same writer to finish a capped 3072-token thinking pass",
    )
    args = cli.parse_args(argv)
    if args.phase == "teach":
        if (
            args.private
            or args.clarified
            or args.deliberate
            or args.preparation_context
            or args.finish_draft
        ):
            cli.error("teach takes just the model and a new ballot output path")
        with args.output.open("x") as log:
            transfer(MODELS[args.model], [], log, control_cue="taught-none")
        return
    if args.private is None:
        cli.error("generate and transfer require both a private note path and an output path")
    model = MODELS[args.model]
    cues = ("deliberate",) if args.deliberate else CUES
    seeds = (1, 2, 3)
    if args.clarified:
        cues, seeds = ("clarified-invariants",), (1,)
    if args.preparation_context:
        cues, seeds = (f"deliberate-{args.preparation_context // 1024}k",), (1,)
    if args.finish_draft:
        cues, seeds = ("finish-draft",), (1,)
    if args.phase == "transfer":
        expected = {(cue, seed) for seed in seeds for cue in cues}
        notes = read_notes(model, args.private, expected)
    with args.output.open("x") as log:
        if args.phase == "generate":
            with open_private(args.private) as owner:
                generate(model, owner, log, seeds, cues)
        else:
            transfer(
                model,
                notes,
                log,
                include_control=not (
                    args.deliberate or args.preparation_context or args.finish_draft
                ),
                control_cue="clarified-none" if args.clarified else "none",
            )
    print(json.dumps(resident_model(model)))


if __name__ == "__main__":
    main()
