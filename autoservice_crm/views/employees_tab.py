from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.employee_service import EmployeeService
from services.errors import DomainError
from views.ui_utils import ask_confirm, busy_cursor, render_table, show_error


class EmployeesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.service = EmployeeService()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        top.addStretch()
        btn_add = QPushButton("Add Employee")
        btn_add.clicked.connect(self._on_add)
        top.addWidget(btn_add)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Commission %", "Created"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(2, 130)
        self.table.setColumnWidth(3, 170)
        layout.addWidget(self.table)

        bottom = QHBoxLayout()
        bottom.addStretch()

        btn_edit = QPushButton("Edit")
        btn_edit.setProperty("variant", "ghost")
        btn_edit.clicked.connect(self._on_edit)
        bottom.addWidget(btn_edit)

        btn_delete = QPushButton("Delete")
        btn_delete.setProperty("variant", "danger")
        btn_delete.clicked.connect(self._on_delete)
        bottom.addWidget(btn_delete)

        layout.addLayout(bottom)

    def refresh(self) -> None:
        with busy_cursor():
            employees = self.service.list_employees()

        def build_row(row: int) -> None:
            emp = employees[row]
            self.table.setItem(row, 0, QTableWidgetItem(str(emp.id)))
            self.table.setItem(row, 1, QTableWidgetItem(emp.full_name))
            self.table.setItem(row, 2, QTableWidgetItem(f"{emp.commission_pct}%"))
            self.table.setItem(row, 3, QTableWidgetItem(emp.created_at or ""))

        render_table(self.table, len(employees), build_row)

    def _get_selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _on_add(self) -> None:
        dialog = EmployeeDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.create_employee(**dialog.get_data())
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc))

    def _on_edit(self) -> None:
        employee_id = self._get_selected_id()
        if not employee_id:
            QMessageBox.warning(self, "Selection", "Select an employee in the table.")
            return
        try:
            employee = self.service.get_employee(employee_id)
            dialog = EmployeeDialog(self, employee)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self.service.update_employee(employee_id, **dialog.get_data())
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc))

    def _on_delete(self) -> None:
        employee_id = self._get_selected_id()
        if not employee_id:
            QMessageBox.warning(self, "Selection", "Select an employee in the table.")
            return
        try:
            employee = self.service.get_employee(employee_id)
            if not ask_confirm(
                self,
                "Confirm Delete",
                (
                    f"Delete employee '{employee.full_name}'?\n\n"
                    "In existing work items, performer will be reset to empty."
                ),
            ):
                return
            self.service.delete_employee(employee_id)
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc))


class EmployeeDialog(QDialog):
    def __init__(self, parent=None, employee=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Employee" if employee else "New Employee")
        self.setMinimumWidth(430)

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        self.name_input = QLineEdit(employee.full_name if employee else "")
        self.name_input.setPlaceholderText("Employee full name")
        layout.addRow("Name *", self.name_input)

        self.pct_input = QSpinBox()
        self.pct_input.setRange(0, 100)
        self.pct_input.setSuffix(" %")
        self.pct_input.setValue(employee.commission_pct if employee else 40)
        layout.addRow("Commission", self.pct_input)

        actions = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("variant", "ghost")
        btn_cancel.clicked.connect(self.reject)
        actions.addWidget(btn_cancel)

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.accept)
        actions.addWidget(btn_save)
        layout.addRow(actions)

        self.name_input.setFocus()

    def get_data(self) -> dict:
        return {
            "full_name": self.name_input.text().strip(),
            "commission_pct": self.pct_input.value(),
        }
