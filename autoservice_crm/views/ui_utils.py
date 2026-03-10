from __future__ import annotations

from contextlib import contextmanager

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QTableWidget, QWidget


def show_error(parent: QWidget, message: str, title: str = "Error") -> None:
    QMessageBox.critical(parent, title, message)


def show_info(parent: QWidget, message: str, title: str = "Done") -> None:
    QMessageBox.information(parent, title, message)


def ask_confirm(parent: QWidget, title: str, message: str) -> bool:
    reply = QMessageBox.question(
        parent,
        title,
        message,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    )
    return reply == QMessageBox.StandardButton.Yes


@contextmanager
def busy_cursor():
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        yield
    finally:
        QApplication.restoreOverrideCursor()


def render_table(table: QTableWidget, row_count: int, row_builder) -> None:
    """
    Small rendering helper: disables updates during table fill to reduce repaint cost.
    """
    table.setUpdatesEnabled(False)
    try:
        table.setRowCount(row_count)
        for row in range(row_count):
            row_builder(row)
    finally:
        table.setUpdatesEnabled(True)
