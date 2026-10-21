from pathlib import Path

from PyQt6.QtWidgets import QApplication

from main_window import MainWindow
from maze import Maze

DEFAULT_MAZE_PATH = Path(__file__).parent / "data" / "maze_15.json"


def main() -> None:
    app = QApplication([])
    if DEFAULT_MAZE_PATH.exists():
        maze = Maze.from_json(DEFAULT_MAZE_PATH)
    else:
        maze = Maze.random(15, 15, 0.3, seed=7)
    window = MainWindow(maze)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
