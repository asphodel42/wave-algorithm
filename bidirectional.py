"""Two-directional wave search: one wave from the start, a counter wave from the target."""

from collections.abc import Iterator
from dataclasses import dataclass
from time import perf_counter

from maze import FREE, Cell, Maze
from wave_algorithm import (
    OPERATORS,
    WaveEvent,
    WaveKind,
    WaveResult,
    backtrace,
    copy_marks,
)

Marks = list[list[int]]


@dataclass
class BiEvent(WaveEvent):
    # inherited `marks`/`front` belong to the start wave, these to the target wave
    back_marks: Marks | None = None
    back_front: list[Cell] | None = None
    side: str = ""  # wave that moved in this step: "s" (from start), "t" (from target), "" (init)
    cycle: int = 0  # outer loop iteration: one start wave + one target wave
    meet: Cell | None = None  # cell labelled by both waves


@dataclass
class BiResult(WaveResult):
    half_waves: int = (
        0  # single-side waves in total (what one-directional search calls cycles)
    )
    meet: Cell | None = None


def expand(
    own: Marks, other: Marks, front: list[Cell], k: int, moves: list[tuple[int, int]]
) -> tuple[list[Cell], Cell | None, int]:
    """Spreads one wave: FREE neighbors of the k-labelled `front` get k+1 in `own`.

    Stops at the first new cell that `other` has already labelled: the waves met there.
    Waves grow by whole layers in turn, so before this step the two labelled areas were
    disjoint, and any meeting cell found now lies on a shortest path.
    Returns (next front, meeting cell or None, front cells expanded).
    """
    rows, cols = len(own), len(own[0])
    next_front: list[Cell] = []
    for i, (row, col) in enumerate(front):
        for dr, dc in moves:
            nr, nc = row + dr, col + dc
            if 0 <= nr < rows and 0 <= nc < cols and own[nr][nc] == FREE:
                own[nr][nc] = k + 1
                next_front.append((nr, nc))
                if other[nr][nc] > 0:
                    return next_front, (nr, nc), i + 1
    return next_front, None, len(front)


def join_path(
    ms: Marks, mt: Marks, meet: Cell, moves: list[tuple[int, int]]
) -> list[Cell]:
    """start -> meet down the start labels, then meet -> target down the target labels."""
    to_start = backtrace(ms, meet, moves)  # [start, ..., meet]
    to_target = backtrace(mt, meet, moves)  # [target, ..., meet]
    return to_start + to_target[-2::-1]


def bi_wave_search(
    maze: Maze, operator: str, snapshots: bool = True
) -> Iterator[BiEvent]:
    """Two-directional wave (Lee) search.

    - two label matrices: ms (start = 1) and mt (target = 1), two fronts fs and ft;
    - one outer iteration = one cycle = the start wave spreads one layer, then the target wave;
    - stop when a wave labels a cell the other wave already holds (FOUND)
      or when either front dies out (DONE: the start and the target are not connected).

    snapshots=False hands out the live matrices instead of copies: used for timing.
    """
    moves = OPERATORS[operator]
    ms, mt = copy_marks(maze.grid), copy_marks(maze.grid)
    ms[maze.start[0]][maze.start[1]] = 1
    mt[maze.target[0]][maze.target[1]] = 1
    fs, ft = [maze.start], [maze.target]
    ks = kt = 1  # number of the current start / target wave
    cycle = expanded = 0

    def event(
        kind: WaveKind,
        side: str,
        path: list[Cell] | None = None,
        meet: Cell | None = None,
    ) -> BiEvent:
        def snap(m: Marks) -> Marks:
            return copy_marks(m) if snapshots else m

        wave = kt if side == "t" else ks
        return BiEvent(
            kind,
            wave,
            fs,
            snap(ms),
            expanded,
            path,
            back_marks=snap(mt),
            back_front=ft,
            side=side,
            cycle=cycle,
            meet=meet,
        )

    yield event(WaveKind.WAVE, "")
    if maze.start == maze.target:
        yield event(WaveKind.FOUND, "", [maze.start], maze.start)
        return

    while fs and ft:  # both waves alive
        cycle += 1

        fs, meet, n = expand(ms, mt, fs, ks, moves)  # half-cycle 1: wave from the start
        ks += 1
        expanded += n
        if meet:
            yield event(WaveKind.FOUND, "s", join_path(ms, mt, meet, moves), meet)
            return
        if not fs:
            break
        yield event(WaveKind.WAVE, "s")

        ft, meet, n = expand(
            mt, ms, ft, kt, moves
        )  # half-cycle 2: wave from the target
        kt += 1
        expanded += n
        if meet:
            yield event(WaveKind.FOUND, "t", join_path(ms, mt, meet, moves), meet)
            return
        if not ft:
            break
        yield event(WaveKind.WAVE, "t")

    yield event(WaveKind.DONE, "")


def solve_bi(maze: Maze, operator: str) -> BiResult:
    t0 = perf_counter()
    for last in bi_wave_search(maze, operator, snapshots=False):
        pass
    seconds = perf_counter() - t0
    # labels start at 1, so a matrix whose top label is m has spread m-1 waves
    half_waves = max(map(max, last.marks)) - 1 + max(map(max, last.back_marks)) - 1
    return BiResult(
        last.kind == WaveKind.FOUND,
        last.path or [],
        last.cycle,
        last.expanded,
        seconds,
        half_waves=half_waves,
        meet=last.meet,
    )
