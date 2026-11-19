"""Play a solitaire game using the same events that power replay."""

from random import Random

from .board import frontier, moves, rotate
from .game import Game
from .record import new_record


def edges(face):
    groups = [
        "".join(name for d, name in enumerate("NESW") if mask & (1 << d)) or "–"
        for mask in (face & 15, face >> 4)
    ]
    return f"in {groups[0]}, out {groups[1]}"


def choose(label, options, describe=str):
    print(f"\n{label}")
    for index, value in enumerate(options, 1):
        print(f"  {index}. {describe(value)}")
    while True:
        answer = input("Choice > ").strip()
        try:
            number = int(answer)
        except ValueError:
            number = 0
        if 1 <= number <= len(options):
            return options[number - 1]
        print(f"Enter a number from 1 through {len(options)}.")


def show_floor(view):
    print(f"\nTurn {view['turn']} · marker {view['marker']} · exit {view['goal']}")
    for cell, face in view["board"]:
        print(f"  {cell}  {edges(face)}")


def play(initial, seed):
    game = Game(initial)
    record = new_record(initial)
    bag = Random(f"draw/{seed}")
    while not game.winner:
        stage = game.stage
        view = game.view(0)
        e = {"kind": stage}
        if stage == "draw":
            show_floor(view)
            count = min(2, view["store_count"])
            e["tiles"] = bag.sample(game.store, count)
            print(f"Store before draw: {view['store_count']}. Drew {e['tiles']}.")
        elif stage == "place":
            face = choose("Tile to place", sorted(view["hand"]), lambda f: f"{f} · {edges(f)}")
            e["tile"] = face
            e["rotation"] = choose(
                "Rotation", range(4), lambda r, f=face: f"{r * 90}° · {edges(rotate(f, r))}"
            )
            e["at"] = list(choose("Placement square", frontier(dict(view["board"]), view["goal"])))
        elif stage == "discard":
            e["tile"] = choose(
                "Return to store", sorted(view["hand"]), lambda f: f"{f} · {edges(f)}"
            )
        elif stage == "propose":
            dest = choose(
                "Marker movement",
                [None, *moves(dict(view["board"]), view["marker"])],
                lambda p: "Stay" if p is None else str(p),
            )
            e["to"] = None if dest is None else list(dest)
        elif stage == "move_vote":
            e["votes"] = [True]
        game.apply(e)
        record["events"].append(e)
    return record
