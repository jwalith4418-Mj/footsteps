"""Fixed-deal real-clock solitaire and social throughput comparisons."""

import argparse
from pathlib import Path
from random import Random

from experiments.persistent_table import play, report
from footsteps.game import with_exit_origin
from footsteps.session import Session
from footsteps.solo import setup
from footsteps.table import Table, paper_setup

MODEL = "qwen3.5:9b-q8_0"
READ_TOOLS = {"get_state", "get_role", "history", "inspect_rotations_at", "preview_placement"}


class RepeatAwareSession(Session):
    """Compare immediate repeated reads on exactly the same private-view cursor."""

    def reset(self, *, recovered=False):
        self.last_query = None
        super().reset(recovered=recovered)

    def execute(self, name, args, offered, revision):
        previous = self.last_query
        self.last_query = None
        result = super().execute(name, args, offered, revision)
        if name not in READ_TOOLS:
            return result
        self.last_query = (name, args, self.cursor)
        if previous != self.last_query:
            return result
        commits = {
            "place_tile",
            "return_tile",
            "propose_step",
            "stay",
            "vote_move",
            "nominate",
            "pass_nomination",
            "vote_removal",
        }
        return {
            "repeat": "Same query and seat view. The last full result still applies. The clock continues.",
            "available_commit_tools": [
                t["function"]["name"] for t in offered if t["function"]["name"] in commits
            ],
        }


class IdleBudgetSession(Session):
    """One background inference per visible change; ordinary discussion and decisions stay open."""

    last_idle_cursor = None

    def step(self, model, **kwargs):
        self.refresh()
        if (
            self.snap["phase"] != "over"
            and self.snap["choices"] is None
            and not self.snap["can_speak"]
        ):
            if self.last_idle_cursor == self.cursor:
                self.wait(self.cursor)
                return None
            self.last_idle_cursor = self.cursor
        return super().step(model, **kwargs)


def deal(mode, seed):
    if mode == "solo":
        return with_exit_origin(setup(seed, (2, 1), 2, 4, 0.55))
    floor = paper_setup(Random(seed), 3)
    floor["goal"] = [2, 0]
    floor["store"] = floor["store"][:3]
    return with_exit_origin(floor)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("mode", choices=("solo", "social"))
    cli.add_argument("root", type=Path)
    cli.add_argument("private", type=Path)
    cli.add_argument("--seed", type=int, default=11301)
    arm = cli.add_mutually_exclusive_group()
    arm.add_argument("--repeat-aware", action="store_true")
    arm.add_argument("--idle-budget", action="store_true")
    args = cli.parse_args()
    seconds = 45
    discussion = 30 if args.mode == "social" else 0
    session_class = Session
    if args.repeat_aware:
        session_class = RepeatAwareSession
    elif args.idle_budget:
        session_class = IdleBudgetSession
    table = Table(deal(args.mode, args.seed), Random(f"draw/{args.seed}"), seconds, discussion)
    play(
        args.root,
        args.private,
        MODEL,
        32768,
        seconds,
        discussion,
        table=table,
        session_class=session_class,
    )
    report(args.root)
