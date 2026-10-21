"""Wave search with the three move operators: fixed mazes, then maze size and wall density."""
from pathlib import Path
from statistics import mean, median

from maze import Maze
from wave_algorithm import OPERATORS, solve

DATA = Path(__file__).parent / "data"
WALLS = 0.3
DATA_SEEDS = {10: 10, 15: 24, 20: 15}  # every operator reaches the target, the cross path has detours
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


def fixed_mazes() -> None:
    print(f"{'Maze':<12} {'Walls':>5} {'Operator':<9} {'Found':>5} {'Len':>4} {'Cycles':>6} {'Exp':>4} {'ms':>7}")
    for n in DATA_SEEDS:
        m = Maze.from_json(DATA / f"maze_{n}.json")
        for op in OPERATORS:
            res = solve(m, op)
            ms = median(solve(m, op).seconds for _ in range(TIMING_RUNS)) * 1000
            length = len(res.path) - 1 if res.found else "-"
            print(f"maze_{n}.json {m.wall_ratio():>5.0%} {op:<9} {str(res.found):>5} {length:>4} "
                  f"{res.cycles:>6} {res.expanded:>4} {ms:>7.3f}")


def size_and_density() -> None:
    print(f"\n{'Size':<6} {'Walls':>5} {'Operator':<9} {'Reach':>6} {'Len':>6} {'Exp':>6} {'ms':>7}")
    for n in SIZES:
        for p in DENSITIES:
            mazes = [Maze.random(n, n, p, seed) for seed in SEEDS]
            runs = {op: [solve(m, op) for m in mazes] for op in OPERATORS}
            for cross, combined in zip(runs["cross"], runs["combined"]):
                if cross.found:
                    assert combined.found and len(combined.path) <= len(cross.path)
            for op, results in runs.items():
                found = [r for r in results if r.found]
                avg_len = mean(len(r.path) - 1 for r in found) if found else float("nan")
                print(f"{n}x{n:<3} {p:>5.0%} {op:<9} {len(found) / len(results):>6.0%} {avg_len:>6.1f} "
                      f"{mean(r.expanded for r in results):>6.1f} {mean(r.seconds for r in results) * 1000:>7.3f}")


def parity() -> None:
    """Diagonal moves keep (row + col) % 2, so half of the cells are out of reach."""
    print("\nEmpty 15x15, start (0,0):")
    for target in ((14, 14), (0, 1)):
        m = Maze.empty(15, 15)
        m.set_target(target)
        cells = [f"{op}={'yes' if solve(m, op).found else 'no'}" for op in OPERATORS]
        print(f"  target {target}: " + ", ".join(cells))


def main() -> None:
    make_data()
    fixed_mazes()
    size_and_density()
    parity()
    print("ok: combined is never longer than cross")


if __name__ == "__main__":
    main()
