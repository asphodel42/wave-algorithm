from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDockWidget,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from animation import AnimationController
from bidirectional import BiEvent, bi_wave_search, solve_bi
from maze import FREE, Maze
from maze_view import MazeView
from results_window import RunRecord, ResultsWindow, cell_label
from wave_algorithm import OPERATOR_LABELS, WaveEvent, WaveKind, solve, wave_search

DATA_DIR = Path(__file__).parent / "data"
SIZE_RANGE = (5, 40)


class MainWindow(QMainWindow):
    def __init__(self, maze: Maze) -> None:
        super().__init__()
        self.setWindowTitle("Двонаправлений хвильовий пошук у лабіринті")
        self.resize(1150, 800)

        self.maze = maze
        self.view = MazeView(maze)
        self.view.cell_clicked.connect(self.on_cell_clicked)
        self.setCentralWidget(self.view)

        self.animation = AnimationController(self)
        self.animation.step_shown.connect(self.on_step)
        self.animation.finished.connect(self.on_finished)
        self.pending_record: RunRecord | None = None
        self.paint_value = FREE  # value a wall-drag paints, fixed by the first click

        self.results = ResultsWindow(self)
        self.setStatusBar(QStatusBar())
        self.build_side_panel()
        self.sync_size_inputs()
        self.maze_changed()

    # ---------- side panel ----------

    def build_side_panel(self) -> None:
        dock = QDockWidget("Керування", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.build_maze_box())
        layout.addWidget(self.build_edit_box())
        layout.addWidget(self.build_search_box())
        layout.addWidget(self.build_playback_box())
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        scroll.setMinimumWidth(270)
        dock.setWidget(scroll)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    def build_maze_box(self) -> QGroupBox:
        box = QGroupBox("Лабіринт")
        form = QFormLayout(box)
        self.rows_input = QSpinBox()
        self.cols_input = QSpinBox()
        for spin in (self.rows_input, self.cols_input):
            spin.setRange(*SIZE_RANGE)
        form.addRow("Рядки:", self.rows_input)
        form.addRow("Стовпці:", self.cols_input)
        resize_button = QPushButton("Застосувати розмір")
        resize_button.clicked.connect(self.apply_size)
        form.addRow(resize_button)

        self.walls_input = QSpinBox()
        self.walls_input.setRange(0, 60)
        self.walls_input.setValue(30)
        self.walls_input.setSuffix(" %")
        form.addRow("Стін:", self.walls_input)
        random_button = QPushButton("Згенерувати")
        random_button.clicked.connect(self.generate_maze)
        clear_button = QPushButton("Очистити")
        clear_button.clicked.connect(self.clear_walls)
        load_button = QPushButton("Відкрити…")
        load_button.clicked.connect(self.load_maze)
        save_button = QPushButton("Зберегти…")
        save_button.clicked.connect(self.save_maze)
        grid = QGridLayout()
        grid.addWidget(random_button, 0, 0)
        grid.addWidget(clear_button, 0, 1)
        grid.addWidget(load_button, 1, 0)
        grid.addWidget(save_button, 1, 1)
        form.addRow(grid)
        return box

    def build_edit_box(self) -> QGroupBox:
        box = QGroupBox("Редагування (клік по клітинці)")
        layout = QVBoxLayout(box)
        self.edit_group = QButtonGroup(self)
        row = QHBoxLayout()
        for i, text in enumerate(("Стіна", "Старт", "Ціль")):
            button = QRadioButton(text)
            button.setChecked(i == 0)
            self.edit_group.addButton(button, i)
            row.addWidget(button)
        layout.addLayout(row)
        hint = QLabel("Стіни можна малювати, протягуючи мишею.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return box

    def build_search_box(self) -> QGroupBox:
        box = QGroupBox("Пошук")
        layout = QVBoxLayout(box)
        self.mode_input = QComboBox()
        self.mode_input.addItem("Двонаправлений", True)
        self.mode_input.addItem("Однонаправлений", False)  # kept for comparison with lab 3
        self.operator_input = QComboBox()
        for key, label in OPERATOR_LABELS.items():
            self.operator_input.addItem(label, key)
        # a recorded run belongs to one mode and operator: switching must not replay the old wave
        self.mode_input.currentIndexChanged.connect(self.maze_changed)
        self.operator_input.currentIndexChanged.connect(self.maze_changed)
        form = QFormLayout()
        form.addRow("Пошук:", self.mode_input)
        form.addRow("Оператор:", self.operator_input)
        layout.addLayout(form)
        numbers = QCheckBox("Показувати числа в клітинках")
        numbers.setChecked(True)
        numbers.toggled.connect(self.view.set_show_numbers)
        layout.addWidget(numbers)
        run_button = QPushButton("Пошук")
        run_button.clicked.connect(self.run_search)
        layout.addWidget(run_button)
        results_button = QPushButton("Вікно результатів")
        results_button.clicked.connect(lambda: (self.results.show(), self.results.raise_()))
        layout.addWidget(results_button)
        return box

    def build_playback_box(self) -> QGroupBox:
        box = QGroupBox("Програвання")
        layout = QVBoxLayout(box)
        grid = QGridLayout()
        self.play_button = QPushButton("Пуск")
        self.play_button.clicked.connect(self.toggle_play)
        buttons = [
            (self.play_button, 0, 0),
            (QPushButton("До кінця"), 0, 1),
            (QPushButton("Крок назад"), 1, 0),
            (QPushButton("Крок вперед"), 1, 1),
            (QPushButton("Скинути"), 2, 0),
        ]
        buttons[1][0].clicked.connect(self.skip_to_end)
        buttons[2][0].clicked.connect(self.animation.step_back)
        buttons[3][0].clicked.connect(self.animation.step_forward)
        buttons[4][0].clicked.connect(self.reset_animation)
        for button, r, c in buttons:
            grid.addWidget(button, r, c)
        layout.addLayout(grid)

        self.delay_label = QLabel()
        layout.addWidget(self.delay_label)
        self.delay_input = QSlider(Qt.Orientation.Horizontal)
        self.delay_input.setRange(0, 1000)
        self.delay_input.setSingleStep(50)
        self.delay_input.setPageStep(100)
        self.delay_input.valueChanged.connect(self.set_delay)
        self.delay_input.setValue(200)
        layout.addWidget(self.delay_input)
        return box

    # ---------- maze editing ----------

    def sync_size_inputs(self) -> None:
        self.rows_input.setValue(self.maze.rows)
        self.cols_input.setValue(self.maze.cols)

    def maze_changed(self) -> None:
        """Any edit makes the recorded wave stale, so it is dropped."""
        self.animation.clear()
        self.pending_record = None
        self.play_button.setText("Пуск")
        self.view.set_maze(self.maze)
        self.statusBar().showMessage(
            f"{self.maze.rows}x{self.maze.cols}, стін {self.maze.wall_ratio():.0%}, "
            f"старт {cell_label(self.maze.start)}, ціль {cell_label(self.maze.target)}"
        )

    def on_cell_clicked(self, row: int, col: int, dragging: bool) -> None:
        cell = (row, col)
        mode = self.edit_group.checkedId()
        if mode == 0:
            if not dragging:
                self.maze.toggle_wall(cell)
                self.paint_value = self.maze.grid[row][col]
            elif self.maze.grid[row][col] != self.paint_value:
                self.maze.toggle_wall(cell)
        elif mode == 1:
            self.maze.set_start(cell)
        else:
            self.maze.set_target(cell)
        self.maze_changed()

    def apply_size(self) -> None:
        self.maze.resize(self.rows_input.value(), self.cols_input.value())
        self.maze_changed()

    def generate_maze(self) -> None:
        self.maze = Maze.random(self.rows_input.value(), self.cols_input.value(), self.walls_input.value() / 100)
        self.maze_changed()

    def clear_walls(self) -> None:
        self.maze.grid = [[FREE] * self.maze.cols for _ in range(self.maze.rows)]
        self.maze_changed()

    def load_maze(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Відкрити лабіринт", str(DATA_DIR), "JSON (*.json)")
        if not path:
            return
        try:
            self.maze = Maze.from_json(path)
        except (OSError, ValueError, KeyError, TypeError, IndexError) as e:
            QMessageBox.warning(self, "Помилка", f"Не вдалося прочитати файл:\n{e}")
            return
        self.sync_size_inputs()
        self.maze_changed()

    def save_maze(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти лабіринт", str(DATA_DIR / "maze.json"), "JSON (*.json)")
        if path:
            self.maze.to_json(path)

    # ---------- search and playback ----------

    def run_search(self) -> None:
        operator = self.operator_input.currentData()
        bi = self.mode_input.currentData()
        result = (solve_bi if bi else solve)(self.maze, operator)  # timed separately from the animation frames
        self.animation.load(list((bi_wave_search if bi else wave_search)(self.maze, operator)))
        self.pending_record = RunRecord(
            operator, f"{self.maze.rows}x{self.maze.cols}", self.maze.wall_ratio(),
            self.maze.start, self.maze.target, result,
        )
        self.animation.play()
        self.play_button.setText("Пауза")

    def on_step(self, event: WaveEvent) -> None:
        self.view.show_event(event)
        if isinstance(event, BiEvent):
            self.statusBar().showMessage(self.bi_status(event))
            return
        text = f"Хвиля {event.wave}: фронт {len(event.front)}, розкрито {event.expanded}"
        if event.kind == WaveKind.FOUND:
            text += f" - ціль знайдено, довжина {len(event.path) - 1}"
        elif event.kind == WaveKind.DONE:
            text += " - хвиля згасла, ціль недосяжна"
        self.statusBar().showMessage(text)

    @staticmethod
    def bi_status(event: BiEvent) -> str:
        wave = {"s": f"хвиля від старту {event.wave}", "t": f"хвиля від цілі {event.wave}'"}.get(event.side, "старт")
        text = (f"Цикл {event.cycle}: {wave}; фронти {len(event.front)} / {len(event.back_front)}, "
                f"розкрито {event.expanded}")
        if event.kind == WaveKind.FOUND:
            text += f" - хвилі зустрілись у {cell_label(event.meet)}, довжина {len(event.path) - 1}"
        elif event.kind == WaveKind.DONE:
            text += " - одна з хвиль згасла, ціль недосяжна"
        return text

    def on_finished(self, _found: bool) -> None:
        self.play_button.setText("Пуск")
        if self.pending_record:
            self.results.add(self.pending_record)
            self.pending_record = None

    def toggle_play(self) -> None:
        if self.animation.is_playing():
            self.animation.pause()
            self.play_button.setText("Пуск")
        elif self.animation.total_steps:
            if self.animation.index >= self.animation.total_steps - 1:
                self.animation.reset()  # replay a finished run from the first wave
            self.animation.play()
            self.play_button.setText("Пауза")
        else:
            self.run_search()

    def skip_to_end(self) -> None:
        if self.animation.total_steps:
            self.animation.goto(self.animation.total_steps - 1)
            self.animation.advance()  # past the last frame -> emits finished

    def reset_animation(self) -> None:
        self.animation.reset()
        self.view.show_event(None)
        self.play_button.setText("Пуск")

    def set_delay(self, ms: int) -> None:
        self.animation.set_speed(ms)
        self.delay_label.setText(f"Затримка між хвилями: {ms} мс")
