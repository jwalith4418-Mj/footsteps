"""Replay ordinary removal ballots with first-person seat identity and attributed evidence."""

import argparse
import json
import re
from itertools import product
from pathlib import Path

from experiments.action_probe import position
from experiments.skill_probe import MODEL
from footsteps.decision_notes import open_private
from footsteps.ollama import decode_choice, model_request, request
from footsteps.social import consequences

ROOT = Path(__file__).parent
CASES = (
    ("goal-pursuit/games/five-9901-last-r320.json", 55),
    ("minority/five-colors/8602-red1+3.json", 12),
)
RELATIONS = ["myself", "known_teammate", "known_opponent", "undisclosed"]


def expected(snap):
    state = snap["state"]
    target = state["pending"]
    if target == snap["seat"]:
        relation = "myself"
    elif state["role"] == "red":
        relation = "known_teammate" if target in state["teammates"] else "known_opponent"
    else:
        relation = "undisclosed"
    prior_yes = any(
        r["text"].startswith("Elimination ballots — ")
        and f"P{target} yes" in r["text"].split(".")[0]
        for r in snap["history"][-12:]
    )
    return {"nominee_relation": relation, "visible_removal_yes_by_nominee": prior_yes}


def presentation(snap, model, identity, sources, quiz, relative=False):
    body = model_request(snap, model, named_ballots=True, explicit_actions=True, explain=True)
    body["think"] = False
    ctx = json.loads(body["messages"][1]["content"])
    if identity:
        private = ctx.pop("your_private_role_information")
        voter = {"seat": f"P{private['seat']}", "private_team": private["alignment"]}
        for key in ("all_blue_seats", "all_red_seats"):
            if key in private:
                voter[key] = [f"P{i}" for i in private[key]]
        # The same seat and roster were already present in the ordinary request.
        for key in ("role", "seat", "teammates"):
            ctx.pop(key, None)
        ctx = {
            "I_am_casting_this_ballot_as": voter,
            "nominee_on_my_ballot": f"P{ctx.pop('pending')}",
            "builder_this_turn": f"P{ctx.pop('actor')}",
            **ctx,
        }
        ctx["alive"] = [f"P{i}" for i in ctx["alive"]]
    if sources:
        recent = []
        for text in ctx["recent"]:
            speaker = re.fullmatch(r"(P\d+): (.*)", text, re.DOTALL)
            recent.append(
                {"speaker": speaker[1], "public_claim": speaker[2]}
                if speaker
                else {"recorded_event": text}
            )
        ctx["recent"] = recent
    if relative:
        me, nominee = snap["seat"], snap["state"]["pending"]
        private = ctx["I_am_casting_this_ballot_as"]
        if me == nominee:
            relation = "I am the nominee."
        elif private["private_team"] == "red":
            relation = (
                "The nominee is on my team."
                if nominee in snap["state"]["teammates"]
                else "The nominee is on the other team."
            )
        else:
            relation = "I was not told the nominee's team."
        ctx["my_relationship_to_the_nominee_at_setup"] = relation
        ctx["if_a_majority_votes_yes"] = (
            "I leave play and still share my team's result."
            if me == nominee
            else f"P{nominee} leaves play and still shares their team's result."
        )
        labels = [label for label, _, _ in consequences(snap)]
        ctx["options"]["vote"] = labels
        body["format"]["properties"]["vote"]["enum"] = labels
    if quiz:
        body["messages"][0]["content"] += (
            " For this separate private fact check, give the nominee's relationship to you "
            "using only the alignment information disclosed at setup (undisclosed if not told). "
            "Also give whether the nominee cast at least one Yes on a removal ballot in the "
            "displayed recent events. Answer these two questions instead of casting a ballot."
        )
        del ctx["options"]
        fields = {
            "nominee_relation": {"type": "string", "enum": RELATIONS},
            "visible_removal_yes_by_nominee": {"type": "boolean"},
        }
        body["format"] = {
            "type": "object",
            "properties": fields,
            "required": list(fields),
            "additionalProperties": False,
        }
    body["messages"][1]["content"] = json.dumps(ctx, separators=(",", ":"))
    return body


def run(model, public, private, relative):
    for source, event in CASES:
        for seat in range(5):
            snap = position(ROOT / source, event - 1, seat)
            assert snap["state"]["stage"] == "eliminate_vote" and seat in snap["state"]["alive"]
            truth = expected(snap)
            conditions = (
                ((True, True, q) for q in (False, True))
                if relative
                else product((False, True), repeat=3)
            )
            for ident, sources, quiz in conditions:
                row = {
                    "source": source,
                    "event": event,
                    "seat": seat,
                    "identity": ident,
                    "sources": sources,
                    "task": "facts" if quiz else "vote",
                    "expected": truth,
                }
                if relative:
                    row["relative"] = True
                body = presentation(snap, model, ident, sources, quiz, relative)
                try:
                    reply = request(11434, "/api/chat", body, 30)
                    row["prompt_tokens"] = reply.get("prompt_eval_count")
                    if reply.get("done_reason") == "length":
                        raise ValueError("reply cap")
                    if quiz:
                        answer = json.loads(reply["message"]["content"])
                        if (
                            not isinstance(answer, dict)
                            or answer.keys() != truth.keys()
                            or answer["nominee_relation"] not in RELATIONS
                            or type(answer["visible_removal_yes_by_nominee"]) is not bool
                        ):
                            raise ValueError("invalid fact reply")
                        row["answer"] = answer
                    else:
                        choice, reason = decode_choice(reply, body, snap["choices"], True)
                        row.update(choice)
                        private.write(json.dumps({**row, "reason": reason}) + "\n")
                        private.flush()
                except (OSError, ValueError) as exc:
                    row["error"] = str(exc)
                public.write(json.dumps(row, separators=(",", ":")) + "\n")
                public.flush()


def self_check(model, output):
    """An independent diagnostic with no game-action instructions or relationship menu."""
    for source, event in CASES:
        for seat in range(5):
            snap = position(ROOT / source, event - 1, seat)
            for relative in (False, True):
                body = presentation(snap, model, relative, relative, False, relative)
                ctx = json.loads(body["messages"][1]["content"])
                del ctx["options"]
                body["messages"] = [
                    {
                        "role": "system",
                        "content": "Read your private table snapshot. Are you the player nominated for removal on this ballot? Answer true or false.",
                    },
                    {"role": "user", "content": json.dumps(ctx, separators=(",", ":"))},
                ]
                body["format"] = {
                    "type": "object",
                    "properties": {"nominee_is_me": {"type": "boolean"}},
                    "required": ["nominee_is_me"],
                    "additionalProperties": False,
                }
                row = {
                    "source": source,
                    "event": event,
                    "seat": seat,
                    "relative": relative,
                    "expected": snap["state"]["pending"] == seat,
                }
                try:
                    reply = request(11434, "/api/chat", body, 30)
                    answer = json.loads(reply["message"]["content"])["nominee_is_me"]
                    if type(answer) is not bool or reply.get("done_reason") == "length":
                        raise ValueError("incomplete self check")
                    row["answer"] = answer
                except (OSError, ValueError, KeyError) as exc:
                    row["error"] = str(exc)
                output.write(json.dumps(row, separators=(",", ":")) + "\n")
                output.flush()


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("output", type=Path)
    cli.add_argument("private_notes", type=Path, nargs="?")
    cli.add_argument(
        "--self-check", action="store_true", help="ask only whether the nominee is the voter"
    )
    cli.add_argument("--model", default=MODEL)
    cli.add_argument(
        "--relative",
        action="store_true",
        help="show the nominee relationship disclosed to this voter",
    )
    args = cli.parse_args()
    if args.self_check:
        if args.private_notes or args.relative:
            cli.error("--self-check takes only the output path")
        with args.output.open("x") as output:
            self_check(args.model, output)
    else:
        if not args.private_notes:
            cli.error("a private note path is required for ballots")
        with args.output.open("x") as public, open_private(args.private_notes) as private:
            run(args.model, public, private, args.relative)
