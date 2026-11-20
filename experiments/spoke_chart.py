"""Render the oriented board and the seat's unrotated hand using the same port glyphs."""


def glyph(name, face):
    if face is None:
        return (" " * 11, ".".center(11), " " * 11)
    ports = ["-iob"[bool(face & (1 << d)) + 2 * bool(face & (16 << d))] for d in range(4)]
    north, east, south, west = ports
    return (north.center(11), f"{west}{name:^9}{east}", south.center(11))


def seat_chart(state):
    marker, goal = tuple(state["marker"]), tuple(state["goal"])
    board = {tuple(p): face for p, face in state["board"]}
    xs, ys = zip(*board, strict=True)
    columns = range(min(xs), max(xs) + 1)
    lines = [
        "North is up. Each tile has a port at N, E, S and W.",
        "i = enter here, o = leave here, b = both, - = closed. . = unbuilt. @ = marker.",
        "Board (installed orientation)",
        "      " + " | ".join(f"x={x}".center(11) for x in columns),
    ]
    for y in range(max(ys), min(ys) - 1, -1):
        cells = []
        for x in columns:
            pos = (x, y)
            face = board.get(pos)
            name = "START" if pos == (0, 0) else "EXIT" if pos == goal else str(face)
            cells.append(glyph(("@" if pos == marker else "") + name, face))
        for row in range(3):
            prefix = f"y={y:>2}  " if row == 1 else "      "
            lines.append(prefix + " | ".join(c[row] for c in cells))
    lines.append("Hand (rotation 0, face number in center)")
    hand = [glyph(str(face), face) for face in state["hand"]]
    lines.extend(" | ".join(row) for row in zip(*hand, strict=True))
    return "\n".join(line.rstrip() for line in lines)
