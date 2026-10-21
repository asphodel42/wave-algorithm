import csv
from dataclasses import dataclass, field
from datetime import datetime

from PyQt6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from maze import Cell
from wave_algorithm import OPERATOR_LABELS, WaveResult

COLUMNS = ["Час", "Оператор", "Розмір", "Стін, %", "Старт", "Ціль", "Знайдено",
           "Довжина", "Циклів", "Розкрито", "Час пошуку, мс"]


def cell_label(cell: Cell) -> str:
    return f"({cell[0]},{cell[1]})"


@dataclass
class RunRecord:
    operator: str
    size: str
    walls: float
    start: Cell
    target: Cell
    result: WaveResult
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%H:%M:%S"))

    def values(self) -> list[str]:
        r = self.result
        return [
            self.timestamp,
            OPERATOR_LABELS[self.operator],
            self.size,
            f"{self.walls * 100:.0f}",
            cell_label(self.start),
            cell_label(self.target),
            "так" if r.found else "ні",
            str(len(r.path) - 1) if r.found else "-",
            str(r.cycles),
            str(r.expanded),
            f"{r.seconds * 1000:.3f}",
        ]

    def path_label(self) -> str:
        return " -> ".join(cell_label(c) for c in self.result.path) if self.result.found else "шлях не знайдено"


class ResultsWindow(QDialog):
    """Separate non-modal window with the history of search runs."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Результати пошуку")
        self.resize(900, 420)
        self.records: list[RunRecord] = []
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.currentCellChanged.connect(lambda row, *_: self.show_path(row))
        layout.addWidget(self.table)

        self.path_title = QLabel("Вершини шляху:")
        layout.addWidget(self.path_title)
        self.path_text = QPlainTextEdit()
        self.path_text.setReadOnly(True)
        self.path_text.setMaximumHeight(90)
        layout.addWidget(self.path_text)

        export_button = QPushButton("Експорт CSV…")
        export_button.clicked.connect(self.export_csv)
        layout.addWidget(export_button)

    def add(self, record: RunRecord) -> None:
        self.records.append(record)
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, value in enumerate(record.values()):
            self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.selectRow(row)
        self.show_path(row)
        self.show()
        self.raise_()

    def show_path(self, row: int) -> None:
        if 0 <= row < len(self.records):
            rec = self.records[row]
            self.path_title.setText(f"Вершини шляху (запуск {rec.timestamp}, {OPERATOR_LABELS[rec.operator]}):")
            self.path_text.setPlainText(rec.path_label())

    def export_csv(self) -> None:
        if not self.records:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Експорт результатів", "wave_log.csv", "CSV (*.csv)")
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8-sig") as f:  # BOM so Excel reads Cyrillic
            writer = csv.writer(f)
            writer.writerow(COLUMNS + ["Шлях"])
            for r in self.records:
                writer.writerow(r.values() + [r.path_label()])
