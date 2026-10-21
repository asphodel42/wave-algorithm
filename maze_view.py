from PyQt6.QtCore import QPointF, QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PyQt6.QtWidgets import QWidget

from maze import WALL, Cell, Maze
from wave_algorithm import WaveEvent

# Color palette
WALL_COLOR = QColor("#424242")
FREE_COLOR = QColor("#f5f5f5")
LABELLED_COLOR = QColor("#c8e6c9")
FRONT_COLOR = QColor("#fff9c4")
PATH_COLOR = QColor("#42a5f5")
START_COLOR = QColor("#66bb6a")
TARGET_COLOR = QColor("#ef5350")
GRID_COLOR = QColor("#bdbdbd")


class MazeView(QWidget):
    """Draws the maze matrix, the wave labels of the current event and the found path."""

    cell_clicked = pyqtSignal(int, int, bool)  # row, col, True while dragging with the button held

    def __init__(self, maze: Maze, parent=None) -> None:
        super().__init__(parent)
        self.maze = maze
        self.event: WaveEvent | None = None
        self.show_numbers = True
        self.last_cell: Cell | None = None
        self.setMinimumSize(300, 300)

    def set_maze(self, maze: Maze) -> None:
        self.maze = maze
        self.event = None
        self.update()

    def show_event(self, event: WaveEvent | None) -> None:
        self.event = event
        self.update()

    def set_show_numbers(self, on: bool) -> None:
        self.show_numbers = on
        self.update()

    def geometry_params(self) -> tuple[float, float, float]:
        """(cell size, x offset, y offset) that center the grid in the widget."""
        size = min(self.width() / self.maze.cols, self.height() / self.maze.rows)
        return size, (self.width() - size * self.maze.cols) / 2, (self.height() - size * self.maze.rows) / 2

    def cell_at(self, pos: QPointF) -> Cell | None:
        size, x0, y0 = self.geometry_params()
        cell = (int((pos.y() - y0) // size), int((pos.x() - x0) // size))
        return cell if self.maze.in_bounds(cell) else None

    def mousePressEvent(self, e) -> None:
        self.last_cell = self.cell_at(e.position())
        if self.last_cell:
            self.cell_clicked.emit(*self.last_cell, False)

    def mouseMoveEvent(self, e) -> None:
        cell = self.cell_at(e.position())
        if cell and cell != self.last_cell and e.buttons() & Qt.MouseButton.LeftButton:
            self.last_cell = cell
            self.cell_clicked.emit(*cell, True)

    def paintEvent(self, _) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().window())
        size, x0, y0 = self.geometry_params()
        ev = self.event
        values = ev.marks if ev else self.maze.grid
        front = set(ev.front) if ev else set()
        path = (ev.path or []) if ev else []
        on_path = set(path)
        font = QFont(self.font())
        font.setPixelSize(max(int(size * 0.38), 6))
        p.setFont(font)

        def rect(cell: Cell) -> QRectF:
            return QRectF(x0 + cell[1] * size, y0 + cell[0] * size, size, size)

        for r in range(self.maze.rows):
            for c in range(self.maze.cols):
                v = values[r][c]
                if v == WALL:
                    color = WALL_COLOR
                elif (r, c) in on_path:
                    color = PATH_COLOR
                elif (r, c) in front:
                    color = FRONT_COLOR
                elif v > 0:
                    color = LABELLED_COLOR
                else:
                    color = FREE_COLOR
                p.fillRect(rect((r, c)), color)
                p.setPen(QPen(GRID_COLOR, 1))
                p.drawRect(rect((r, c)))

        if len(path) > 1:  # the line makes diagonal steps visible
            p.setPen(QPen(QColor("#1565c0"), max(size * 0.08, 2), cap=Qt.PenCapStyle.RoundCap))
            p.drawPolyline(QPolygonF([rect(cell).center() for cell in path]))

        if self.show_numbers and size >= 14:
            for r in range(self.maze.rows):
                for c in range(self.maze.cols):
                    v = values[r][c]
                    p.setPen(QColor("#f5f5f5") if v == WALL else QColor("#212121"))
                    p.drawText(rect((r, c)), Qt.AlignmentFlag.AlignCenter, str(v))

        for cell, color in ((self.maze.start, START_COLOR), (self.maze.target, TARGET_COLOR)):
            p.setPen(QPen(color, max(size * 0.14, 3)))
            p.drawRect(rect(cell).adjusted(2, 2, -2, -2))
        p.end()
