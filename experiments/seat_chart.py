"""One board vertex per square, sharing a directional key with the private hand."""

from footsteps.ollama import tile


def seat_chart(state):
    marker, goal = tuple(state["marker"]), tuple(state["goal"])
    labels = {}
    faces = set(state["hand"])
    for point, face in state["board"]:
        pos = tuple(point)
        if pos == (0, 0):
            name = "S"
        elif pos == goal:
            name = "X"
        else:
            name = str(face)
            faces.add(face)
        labels[pos] = ("@" if pos == marker else "") + name
    xs, ys = zip(*labels, strict=True)
    columns = range(min(xs), max(xs) + 1)
    width = max(map(len, [*labels.values(), str(min(xs)), str(max(xs))]))

    def row(values):
        return " ".join(str(v).rjust(width) for v in values)

    lines = ["S START, X EXIT (both open), @ marker, . unbuilt", "y/x " + row(columns)]
    for y in range(max(ys), min(ys) - 1, -1):
        lines.append(f"{y:>3} " + row(labels.get((x, y), ".") for x in columns))
    lines.append("Hand: " + " ".join(map(str, state["hand"])))
    key = []
    for face in sorted(faces):
        _, incoming, outgoing = tile(face)
        key.append(f"{face}={incoming}>{outgoing}")
    lines.append("Face=in>out: " + " ".join(key))
    return "\n".join(lines)
