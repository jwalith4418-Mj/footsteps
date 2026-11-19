import argparse
import json
from pathlib import Path

from .record import read, render
from .solo import POLICIES, setup, simulate
from .terminal import play


def main():
    parser = argparse.ArgumentParser(description="Play or replay Footsteps")
    sub = parser.add_subparsers(dest="command", required=True)
    solo = sub.add_parser("solo", help="run one solitaire policy and print its account")
    solo.add_argument("--policy", choices=("human", *POLICIES), default="exits")
    solo.add_argument("--seed", type=int, default=0)
    solo.add_argument("--goal", nargs=2, type=int, default=(4, 2))
    solo.add_argument("--hand", type=int, default=2)
    solo.add_argument("--store", type=int, default=10, help="tiles after deal")
    solo.add_argument("--density", type=float, default=0.55)
    solo.add_argument("--save", type=Path, help="write full referee JSON")
    replay = sub.add_parser("replay", help="validate JSON or a full Markdown account")
    replay.add_argument("path", type=Path)
    view = replay.add_mutually_exclusive_group()
    view.add_argument("--seat", type=int)
    view.add_argument("--full", action="store_true", help="embed all secrets for import")
    args = parser.parse_args()
    try:
        if args.command == "solo":
            if args.hand < 0 or args.store < 1 or not 0 <= args.density <= 1:
                parser.error("hand >= 0, store >= 1, density between 0 and 1 required")
            initial = setup(args.seed, args.goal, args.hand, args.store, args.density)
            if args.policy == "human":
                rec = play(initial, args.seed)
            else:
                _, rec = simulate(initial, args.seed, args.policy, capture=True)
            if args.save:
                args.save.write_text(json.dumps(rec, indent=2) + "\n")
            print(render(rec), end="")
        else:
            print(render(read(args.path), seat=args.seat, full=args.full), end="")
    except (EOFError, KeyboardInterrupt):
        parser.exit(1, "\nGame interrupted.\n")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        parser.exit(2, f"footsteps: {e}\n")


if __name__ == "__main__":
    main()
