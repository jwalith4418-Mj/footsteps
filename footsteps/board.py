"""A face has incoming bits NESW in its low nibble and outgoing bits above."""

from collections import deque
from functools import cache

START = (0, 0)
OPEN = 255
STEPS = ((0, 1), (1, 0), (0, -1), (-1, 0))


def neighbors(point):
    x, y = point
    return tuple((x + dx, y + dy) for dx, dy in STEPS)


@cache
def rotate(face, quarter_turns):
    def spin(mask):
        return ((mask << quarter_turns) | (mask >> (4 - quarter_turns))) & 15

    return spin(face >> 4) << 4 | spin(face & 15)


def connects(source, target, direction):
    return bool(source & (16 << direction) and target & (1 << ((direction + 2) % 4)))


def frontier(board, goal):
    return sorted({p for cell in board if cell != goal for p in neighbors(cell) if p not in board})


def moves(board, marker):
    return [
        p
        for d, p in enumerate(neighbors(marker))
        if p in board and connects(board[marker], board[p], d)
    ]


def distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def optimistic_length(board, start, goal, budget):
    """Shortest route within the horizon if every unbuilt tile connects in all directions."""
    queue = deque([(start, 0)])
    seen = {start}
    while queue:
        pos, length = queue.popleft()
        if pos == goal:
            return length
        if length + distance(pos, goal) > budget:
            continue
        for direction, dest in enumerate(neighbors(pos)):
            if dest not in seen and connects(
                board.get(pos, OPEN), board.get(dest, OPEN), direction
            ):
                seen.add(dest)
                queue.append((dest, length + 1))
    return None
