import argparse
import json
from contextlib import nullcontext
from functools import partial
from getpass import getpass
from pathlib import Path

from .action_tools import native_decision
from .decision_notes import open_private, read_notes, save_private_export
from .game import with_exit_origin
from .ollama import Seat, infer, play_seat
from .record import read, render
from .solo import POLICIES, setup, simulate
from .table_server import serve
from .terminal import play
from .viewer import export_html


def main():
    parser = argparse.ArgumentParser(description="Play or replay Footsteps")
    sub = parser.add_subparsers(dest="command", required=True)
    solo = sub.add_parser("solo", help="run one solitaire policy and print its account")
    solo.add_argument("--policy", choices=("human", *POLICIES), default="exits")
    solo.add_argument("--seed", type=int, default=0)
    solo.add_argument(
        "--goal", nargs=2, type=int, default=(4, 2), help="EXIT offset east and north from START"
    )
    solo.add_argument("--hand", type=int, default=2)
    solo.add_argument("--store", type=int, default=10, help="tiles after deal")
    solo.add_argument("--density", type=float, default=0.55)
    solo.add_argument("--save", type=Path, help="write full referee JSON")
    replay = sub.add_parser("replay", help="validate JSON or a full Markdown account")
    replay.add_argument("path", type=Path)
    view = replay.add_mutually_exclusive_group()
    view.add_argument("--seat", type=int)
    view.add_argument("--full", action="store_true", help="embed all secrets for import")
    viewer = sub.add_parser("view", help="export an offline interactive HTML transcript")
    viewer.add_argument("path", type=Path, help="JSON record or full Markdown account")
    perspective = viewer.add_mutually_exclusive_group()
    perspective.add_argument("--omniscient", action="store_true", help="show every hand and role")
    perspective.add_argument("--seat", type=int, help="include this seat's private information")
    viewer.add_argument(
        "--notes",
        type=Path,
        action="append",
        default=[],
        help="attach a private JSONL file to an omniscient export (repeat per seat)",
    )
    viewer.add_argument("-o", "--output", type=Path, required=True, help="destination HTML file")
    table = sub.add_parser("table", help="host a paper-kit table on localhost")
    table.add_argument(
        "--private-rotations",
        type=Path,
        help="record private hand turns to a new owner-only JSONL attachment",
    )
    table.add_argument("--save", required=True, type=Path, help="new private referee JSON path")
    table.add_argument(
        "--port", default=0, type=int, help="loopback port (default: choose a free port)"
    )
    table.add_argument(
        "--seats", type=int, choices=(3, 4), default=4, help="paper-kit player count"
    )
    table.add_argument("--seconds", default=60, type=float, help="seconds per decision")
    table.add_argument(
        "--discussion", default=15, type=float, help="discussion seconds before each ballot"
    )
    supply = table.add_mutually_exclusive_group()
    supply.add_argument(
        "--kit-counts",
        nargs=2,
        type=int,
        metavar=("IN", "OUT"),
        help="uniformly allocate each count among 64 sides of sixteen tiles",
    )
    table.add_argument("--kit-seed", type=int, help="reproduce the tile mix for --kit-counts")
    supply.add_argument(
        "--crossing", action="store_true", help="use the public two-turn demo setup"
    )
    for command in (solo, table):
        origins = command.add_mutually_exclusive_group()
        origins.add_argument(
            "--exit-origin",
            dest="exit_origin",
            action="store_true",
            default=True,
            help="use the default EXIT-centered coordinates",
        )
        origins.add_argument(
            "--start-origin",
            dest="exit_origin",
            action="store_false",
            help="use the historical START-centered coordinates",
        )
    table.add_argument(
        "--placement-check",
        choices=("edge", "edge-and-marker"),
        help="ask builders to classify a directed edge before committing their tile",
    )
    model = sub.add_parser("ollama", help="join a private seat with a local Ollama model")
    model.add_argument("--model", required=True, help="installed Ollama model name")
    model.add_argument("--budget", type=float, default=30, help="maximum seconds per inference")
    model.add_argument(
        "--social-policy",
        choices=("assisted", "prompt"),
        help="frame decisions around the seat's team; assisted also prefers provable team outcomes",
    )
    model.add_argument(
        "--guided", action="store_true", help="supply forward-build examples and team guidance"
    )
    model.add_argument(
        "--named-moves",
        action="store_true",
        help="ask for compass directions when proposing movement",
    )
    model.add_argument(
        "--no-think", action="store_true", help="disable Ollama thinking for this seat"
    )
    model.add_argument(
        "--rotation-aid",
        choices=("table", "tool"),
        help="show the builder all held orientations or offer a private face lookup",
    )
    model.add_argument(
        "--named-rotations",
        action="store_true",
        help="answer placement rotation with an absolute turn name",
    )
    model.add_argument("--named-ballots", action="store_true", help="vote using approve and reject")
    model.add_argument(
        "--tools", action="store_true", help="let the model consult one stage-specific board tool"
    )
    model.add_argument(
        "--private-notes",
        type=Path,
        help="save short model explanations to a new private JSONL file",
    )
    model.add_argument(
        "--action-brief",
        action="store_true",
        help="describe the effect of the current action and name ballot outcomes",
    )
    model.add_argument(
        "--action-tools",
        choices=("direct", "hand"),
        help="commit builds using native tools and literal coordinates",
    )
    model.add_argument(
        "--all-decisions",
        action="store_true",
        help="use native commits on returns, proposals, ballots and nominations too",
    )
    args = parser.parse_args()
    if args.command == "ollama" and args.all_decisions and not args.action_tools:
        parser.error("--all-decisions requires --action-tools")
    try:
        if args.command == "ollama":
            seat = Seat(getpass("Private seat link: ").strip())
            with open_private(args.private_notes) if args.private_notes else nullcontext() as notes:
                ordinary = partial(
                    infer,
                    guided=args.guided,
                    social_guidance=args.social_policy == "prompt",
                    outcome_policy=args.social_policy == "assisted",
                    named_moves=args.named_moves,
                    no_think=args.no_think,
                    named_ballots=args.named_ballots or args.action_brief,
                    explicit_actions=args.action_brief,
                    use_tools=args.tools,
                    rotation_aid=args.rotation_aid,
                    named_rotations=args.named_rotations,
                    note_file=notes,
                )

                def decide(snap, model, seconds):
                    if args.action_tools and (
                        args.all_decisions or snap["state"]["stage"] == "place"
                    ):
                        return native_decision(
                            snap,
                            model,
                            seconds,
                            mode=args.action_tools,
                            guided=args.guided,
                            note_file=notes,
                            orient=lambda h, r: seat.call(
                                "/orient", {"revision": snap["revision"], "piece": h, "rotation": r}
                            ),
                        )
                    return ordinary(snap, model, seconds)

                play_seat(
                    seat, args.model, args.budget, request_note_id=notes is not None, decide=decide
                )
        elif args.command == "table":
            if not 0 <= args.port <= 65535:
                parser.error("--port must be between 0 and 65535")
            if args.crossing and args.seats != 4:
                parser.error("the crossing example requires four seats")
            if args.kit_seed is not None and args.kit_counts is None:
                parser.error("--kit-seed requires --kit-counts")
            serve(args)
        elif args.command == "solo":
            if args.hand < 0 or args.store < 1 or not 0 <= args.density <= 1:
                parser.error("hand >= 0, store >= 1, density between 0 and 1 required")
            initial = setup(args.seed, args.goal, args.hand, args.store, args.density)
            if args.exit_origin:
                initial = with_exit_origin(initial)
            if args.policy == "human":
                rec = play(initial, args.seed)
            else:
                _, rec = simulate(initial, args.seed, args.policy, capture=True)
            if args.save:
                args.save.write_text(json.dumps(rec, indent=2) + "\n")
            print(render(rec), end="")
        elif args.command == "view":
            if args.output.resolve() == args.path.resolve() or (
                args.output.exists() and args.output.samefile(args.path)
            ):
                parser.error("choose an HTML output file separate from the input record")
            if args.notes and not args.omniscient:
                parser.error("--notes requires --omniscient")
            if any(
                args.output.resolve() == p.resolve()
                or (args.output.exists() and args.output.samefile(p))
                for p in args.notes
            ):
                parser.error("choose an output separate from all private notes")
            document = export_html(
                read(args.path),
                args.path.stem,
                args.seat,
                omniscient=args.omniscient,
                notes=read_notes(args.notes),
            )
            if args.notes:
                save_private_export(args.output, document)
            else:
                args.output.write_text(document, encoding="utf-8")
            print(args.output.resolve())
        else:
            print(render(read(args.path), seat=args.seat, full=args.full), end="")
    except (EOFError, KeyboardInterrupt):
        parser.exit(1, "\nGame interrupted.\n")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        parser.exit(2, f"footsteps: {e}\n")


if __name__ == "__main__":
    main()
