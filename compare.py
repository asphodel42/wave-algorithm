"""One- vs two-directional wave search: fixed mazes, maze size and wall density, unreachable target."""

from pathlib import Path
from statistics import mean, median

from bidirectional import solve_bi
from maze import WALL, Maze
from wave_algorithm import OPERATORS, solve

DATA = Path(__file__).parent / "data"
WALLS = 0.3
DATA_SEEDS = {10: 10, 15: 24, 20: 15}
SIZES = (10, 15, 20)
DENSITIES = (0.0, 0.1, 0.2, 0.3, 0.4)
SEEDS = range(100)
TIMING_RUNS = 20


def make_data() -> None:
    DATA.mkdir(exist_ok=True)
    for n, seed in DATA_SEEDS.items():
        path = DATA / f"maze_{n}.json"
        if not path.exists():
            Maze.random(n, n, WALLS, seed).to_json(path)


def check_path(maze: Maze, path: list, moves: list) -> None:
    """The path goes start -> target over free cells, one operator move per step."""
    assert path[0] == maze.start and path[-1] == maze.target
    assert all(maze.is_free(cell) for cell in path)
    assert all((b[0] - a[0], b[1] - a[1]) in moves for a, b in zip(path, path[1:]))


def check(maze: Maze, op: str):
    uni, bi = solve(maze, op), solve_bi(maze, op)
    assert uni.found == bi.found, (op, maze.start, maze.target)
    if bi.found:
        assert len(bi.path) == len(uni.path), (
            op,
            len(uni.path),
            len(bi.path),
        )  # both are shortest
        check_path(maze, bi.path, OPERATORS[op])
        assert (
            bi.half_waves == uni.cycles
        )  # the two waves together cover the same distance
    return uni, bi


def ms(fn, maze: Maze, op: str) -> float:
    return median(fn(maze, op).seconds for _ in range(TIMING_RUNS)) * 1000


def fixed_mazes() -> None:
    print(
        f"{'Maze':<12} {'Operator':<9} {'Len':>4} {'Cyc 1/2':>8} {'Exp 1/2':>9} {'ms 1/2':>13} {'Meet':>8}"
    )
    for n in DATA_SEEDS:
        m = Maze.from_json(DATA / f"maze_{n}.json")
        for op in OPERATORS:
            uni, bi = check(m, op)
            length = len(bi.path) - 1 if bi.found else "-"
            print(
                f"maze_{n}.json {op:<9} {length:>4} {uni.cycles:>4}/{bi.cycles:<3} "
                f"{uni.expanded:>4}/{bi.expanded:<4} {ms(solve, m, op):>6.3f}/{ms(solve_bi, m, op):<6.3f} "
                f"{str(bi.meet):>8}"
            )


def size_and_density() -> None:
    print(
        f"\n{'Size':<6} {'Walls':>5} {'Operator':<9} {'Reach':>6} {'Exp 1':>6} {'Exp 2':>6} "
        f"{'2/1':>5} {'ms 1':>6} {'ms 2':>6}"
    )
    for n in SIZES:
        for p in DENSITIES:
            mazes = [Maze.random(n, n, p, seed) for seed in SEEDS]
            for op in OPERATORS:
                runs = [check(m, op) for m in mazes]
                exp_uni = mean(u.expanded for u, _ in runs)
                exp_bi = mean(b.expanded for _, b in runs)
                print(
                    f"{n}x{n:<3} {p:>5.0%} {op:<9} {mean(b.found for _, b in runs):>6.0%} "
                    f"{exp_uni:>6.1f} {exp_bi:>6.1f} {exp_bi / exp_uni:>5.2f} "
                    f"{mean(u.seconds for u, _ in runs) * 1000:>6.3f} "
                    f"{mean(b.seconds for _, b in runs) * 1000:>6.3f}"
                )


def unreachable() -> None:
    """Target walled in on an empty 20x20: the target wave dies at once, the start wave floods everything."""
    m = Maze.empty(20, 20)
    m.set_target((10, 10))
    for r in range(9, 12):
        for c in range(9, 12):
            if (r, c) != m.target:
                m.grid[r][c] = WALL
    print("\nTarget (10,10) walled in, empty 20x20, start (0,0):")
    for op in OPERATORS:
        uni, bi = check(m, op)
        print(
            f"  {op:<9} one-directional: {uni.expanded:>3} cells, {uni.cycles:>2} cycles; "
            f"two-directional: {bi.expanded:>3} cells, {bi.cycles:>2} cycles"
        )


def edge_cases() -> None:
    m = Maze.empty(5, 5)
    m.set_target((0, 1))  # neighbors: the start wave meets the target cell itself
    for op in ("cross", "combined"):
        assert check(m, op)[1].path == [(0, 0), (0, 1)]
    assert not check(m, "diagonal")[1].found  # (r + c) parity differs
    m.set_target((1, 1))
    assert check(m, "diagonal")[1].path == [(0, 0), (1, 1)]


def main() -> None:
    make_data()
    edge_cases()
    fixed_mazes()
    size_and_density()
    unreachable()
    print("ok: two-directional paths are valid and as short as one-directional ones")


if __name__ == "__main__":
    main()
