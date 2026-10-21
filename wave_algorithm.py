from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum, auto
from time import perf_counter

from maze import FREE, Cell, Maze

CROSS = [(-1, 0), (0, 1), (1, 0), (0, -1)]
DIAGONAL = [(-1, 1), (1, 1), (1, -1), (-1, -1)]
OPERATORS: dict[str, list[tuple[int, int]]] = {
    "cross": CROSS,
    "diagonal": DIAGONAL,
    "combined": CROSS + DIAGONAL,
}
OPERATOR_LABELS = {"cross": "Вверх-вниз-вправо-вліво", "diagonal": "Діагоналі", "combined": "Комбінований"}


class WaveKind(Enum):
    WAVE = auto()    # a new wave front was labelled
    FOUND = auto()   # the target got a label -> search stops, path is the answer
    DONE = auto()    # the wave died out, the target is unreachable


@dataclass
class WaveEvent:
    kind: WaveKind
    wave: int                 # label of the cells in `front`
    front: list[Cell]         # cells labelled in this wave
    marks: list[list[int]]    # copy of the label matrix
    expanded: int             # cells expanded so far
    path: list[Cell] | None = None


@dataclass
class WaveResult:
    found: bool
    path: list[Cell]
    cycles: int               # waves spread before the target got its label
    expanded: int
    seconds: float


def copy_marks(marks: list[list[int]]) -> list[list[int]]:
    """Returns an independent copy of the matrix: changing one never changes the other."""
    copy = []
    for row in marks:
        copy.append(list(row))
    return copy


def backtrace(marks: list[list[int]], target: Cell, moves: list[tuple[int, int]]) -> list[Cell]:
    """Walks from the target down the labels (m, m-1, ..., 1) back to the start."""
    path = [target]
    while marks[path[-1][0]][path[-1][1]] > 1:
        r, c = path[-1]
        want = marks[r][c] - 1
        for dr, dc in moves:  # every operator is symmetric, so the same moves lead back
            nr, nc = r + dr, c + dc
            if 0 <= nr < len(marks) and 0 <= nc < len(marks[0]) and marks[nr][nc] == want:
                path.append((nr, nc))
                break
    path.reverse()
    return path


def wave_search(maze: Maze, operator: str, snapshots: bool = True) -> Iterator[WaveEvent]:
    """One-directional wave (Lee) search.

    - the start gets label 1; every FREE (0) neighbor of a wave-k cell gets k+1;
    - the labels in the matrix replace both the closed list and the parent pointers;
    - one iteration of the outer loop = one wave = one expansion cycle;
    - the target is checked when it gets its label, then the path is read back
      by descending labels.

    snapshots=False hands out the live label matrix instead of a copy per wave:
    used for timing, where the copies would be measured as search work.
    """
    moves = OPERATORS[operator]
    marks = copy_marks(maze.grid)

    def snapshot() -> list[list[int]]:
        """Label matrix handed out with an event."""
        if snapshots:
            return copy_marks(marks)
        return marks

    start_row, start_col = maze.start
    marks[start_row][start_col] = 1
    front = [maze.start]  # cells of the current wave
    k = 1                 # number of the current wave
    expanded = 0
    yield WaveEvent(WaveKind.WAVE, k, front, snapshot(), expanded)

    if maze.start == maze.target:
        yield WaveEvent(WaveKind.FOUND, k, front, snapshot(), expanded, [maze.start])
        return

    while front:  # one iteration = one wave = one expansion cycle
        next_front: list[Cell] = []
        for row, col in front:
            expanded += 1
            for dr, dc in moves:
                neighbor = (row + dr, col + dc)
                n_row, n_col = neighbor
                if maze.in_bounds(neighbor) and marks[n_row][n_col] == FREE:
                    marks[n_row][n_col] = k + 1
                    next_front.append(neighbor)
                    if neighbor == maze.target:
                        path = backtrace(marks, neighbor, moves)
                        yield WaveEvent(WaveKind.FOUND, k + 1, next_front, snapshot(), expanded, path)
                        return
        front = next_front
        k += 1
        if front:
            yield WaveEvent(WaveKind.WAVE, k, front, snapshot(), expanded)

    yield WaveEvent(WaveKind.DONE, k, [], snapshot(), expanded)


def solve(maze: Maze, operator: str) -> WaveResult:
    t0 = perf_counter()
    for last in wave_search(maze, operator, snapshots=False):
        pass
    seconds = perf_counter() - t0
    if last.kind == WaveKind.FOUND:
        return WaveResult(True, last.path, last.wave - 1, last.expanded, seconds)
    return WaveResult(False, [], last.wave - 1, last.expanded, seconds)
