import json
import random as rnd
from dataclasses import dataclass

WALL, FREE = -1, 0
Cell = tuple[int, int]  # (row, col)


@dataclass
class Maze:
    """Unit graph as a maze matrix: WALL (-1) is impassable, FREE (0) is passable."""

    grid: list[list[int]]
    start: Cell
    target: Cell

    @property
    def rows(self) -> int:
        return len(self.grid)

    @property
    def cols(self) -> int:
        return len(self.grid[0])

    def in_bounds(self, cell: Cell) -> bool:
        return 0 <= cell[0] < self.rows and 0 <= cell[1] < self.cols

    def is_free(self, cell: Cell) -> bool:
        return self.in_bounds(cell) and self.grid[cell[0]][cell[1]] == FREE

    def toggle_wall(self, cell: Cell) -> None:
        if cell in (self.start, self.target) or not self.in_bounds(cell):
            return
        r, c = cell
        self.grid[r][c] = FREE if self.grid[r][c] == WALL else WALL

    def set_start(self, cell: Cell) -> None:
        if self.in_bounds(cell) and cell != self.target:
            self.start = cell
            self.grid[cell[0]][cell[1]] = FREE

    def set_target(self, cell: Cell) -> None:
        if self.in_bounds(cell) and cell != self.start:
            self.target = cell
            self.grid[cell[0]][cell[1]] = FREE

    def resize(self, rows: int, cols: int) -> None:
        """Keeps the top-left overlap, new cells are FREE, start/target are pulled inside."""
        self.grid = [
            [self.grid[r][c] if r < self.rows and c < self.cols else FREE for c in range(cols)]
            for r in range(rows)
        ]
        self.start = (min(self.start[0], rows - 1), min(self.start[1], cols - 1))
        self.target = (min(self.target[0], rows - 1), min(self.target[1], cols - 1))
        if self.start == self.target:
            opposite = (rows - 1 - self.start[0], cols - 1 - self.start[1])
            self.target = opposite if opposite != self.start else (0, 0)
        for r, c in (self.start, self.target):
            self.grid[r][c] = FREE

    def wall_ratio(self) -> float:
        return sum(v == WALL for row in self.grid for v in row) / (self.rows * self.cols)

    @classmethod
    def empty(cls, rows: int, cols: int) -> "Maze":
        return cls([[FREE] * cols for _ in range(rows)], (0, 0), (rows - 1, cols - 1))

    @classmethod
    def random(cls, rows: int, cols: int, wall_ratio: float, seed: int | None = None) -> "Maze":
        rng = rnd.Random(seed)
        maze = cls.empty(rows, cols)
        maze.grid = [[WALL if rng.random() < wall_ratio else FREE for _ in range(cols)] for _ in range(rows)]
        for r, c in (maze.start, maze.target):
            maze.grid[r][c] = FREE
        return maze

    def to_json(self, path) -> None:
        # one matrix row per line, so the -1/0 maze is readable in a text editor
        rows = ",\n".join("    " + json.dumps(row) for row in self.grid)
        with open(path, "w", encoding="utf-8") as f:
            f.write(f'{{\n  "rows": {self.rows},\n  "cols": {self.cols},\n'
                    f'  "start": {list(self.start)},\n  "target": {list(self.target)},\n'
                    f'  "grid": [\n{rows}\n  ]\n}}\n')

    @classmethod
    def from_json(cls, path) -> "Maze":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        grid = data["grid"]
        if not (isinstance(grid, list) and grid and all(isinstance(row, list) and row for row in grid)
                and all(len(row) == len(grid[0]) for row in grid)):
            raise ValueError("grid must be a non-empty rectangular matrix")
        if any(type(v) is not int or v not in (WALL, FREE) for row in grid for v in row):
            raise ValueError("grid cells must be -1 (wall) or 0 (free)")
        maze = cls(grid, (0, 0), (0, 0))
        endpoints = []
        for key in ("start", "target"):
            cell = data[key]
            if not (isinstance(cell, list) and len(cell) == 2 and all(type(v) is int for v in cell)
                    and maze.in_bounds(tuple(cell))):
                raise ValueError(f"{key} must be a [row, col] pair inside the grid")
            endpoints.append(tuple(cell))
        maze.start, maze.target = endpoints
        for r, c in endpoints:
            maze.grid[r][c] = FREE
        return maze
