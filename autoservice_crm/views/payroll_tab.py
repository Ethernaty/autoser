from __future__ import annotations

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QDateEdit,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.payroll_service import PayrollService
from views.ui_utils import busy_cursor, render_table


class PayrollTab(QWidget):
    def __init__(self):
        super().__init__()
        self.service = PayrollService()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        top.addWidget(QLabel("From:"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_from.setDisplayFormat("dd.MM.yyyy")
        top.addWidget(self.date_from)

        top.addWidget(QLabel("To:"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat("dd.MM.yyyy")
        top.addWidget(self.date_to)

        btn_calc = QPushButton("Calculate")
        btn_calc.clicked.connect(self._calculate)
        top.addWidget(btn_calc)
        top.addStretch()

        self.total_label = QLabel("")
        self.total_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        top.addWidget(self.total_label)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(
            ["Employee", "Commission", "Works", "Work Total", "Payout"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

    def refresh(self) -> None:
        # Manual calculation by date range.
        return

    def _calculate(self) -> None:
        if self.date_from.date() > self.date_to.date():
            QMessageBox.warning(self, "Invalid Period", "Start date cannot be after end date.")
            return

        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")

        with busy_cursor():
            rows = self.service.calculate(date_from, date_to)

        grand_total = sum(row.payout for row in rows)

        def build_row(i: int) -> None:
            row = rows[i]
            self.table.setItem(i, 0, QTableWidgetItem(row.employee_name))
            self.table.setItem(i, 1, QTableWidgetItem(f"{row.commission_pct}%"))
            self.table.setItem(i, 2, QTableWidgetItem(str(row.work_count)))
            self.table.setItem(i, 3, QTableWidgetItem(f"{row.work_total:,.2f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{row.payout:,.2f}"))

        render_table(self.table, len(rows), build_row)
        self.total_label.setText(f"Total payout: {grand_total:,.2f}")

        if not rows:
            QMessageBox.information(self, "Result", "No completed work items in this period.")
