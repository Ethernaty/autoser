from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from services.client_service import ClientService
from services.errors import DomainError
from views.ui_utils import ask_confirm, busy_cursor, render_table, show_error


class ClientsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.service = ClientService()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or phone")
        self.search_input.textChanged.connect(self.refresh)
        top.addWidget(self.search_input)

        btn_add = QPushButton("Add Client")
        btn_add.clicked.connect(self._on_add)
        top.addWidget(btn_add)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ID", "Name", "Phone", "Notes", "Created"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(4, 160)
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
        search = self.search_input.text().strip() if hasattr(self, "search_input") else ""
        with busy_cursor():
            clients = self.service.list_clients(search)

        def build_row(row: int) -> None:
            client = clients[row]
            self.table.setItem(row, 0, QTableWidgetItem(str(client.id)))
            self.table.setItem(row, 1, QTableWidgetItem(client.full_name))
            self.table.setItem(row, 2, QTableWidgetItem(client.phone))
            self.table.setItem(row, 3, QTableWidgetItem(client.notes))
            self.table.setItem(row, 4, QTableWidgetItem(client.created_at or ""))

        render_table(self.table, len(clients), build_row)

    def _get_selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _on_add(self) -> None:
        dialog = ClientDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.create_client(**dialog.get_data())
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc), title="Validation Error")

    def _on_edit(self) -> None:
        client_id = self._get_selected_id()
        if not client_id:
            QMessageBox.warning(self, "Selection", "Select a client in the table.")
            return
        try:
            client = self.service.get_client(client_id)
            dialog = ClientDialog(self, client)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self.service.update_client(client_id, **dialog.get_data())
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc))

    def _on_delete(self) -> None:
        client_id = self._get_selected_id()
        if not client_id:
            QMessageBox.warning(self, "Selection", "Select a client in the table.")
            return
        try:
            client = self.service.get_client(client_id)
            approved = ask_confirm(
                self,
                "Confirm Delete",
                (
                    f"Delete client '{client.full_name}'?\n\n"
                    "All related vehicles, work orders and work items will also be deleted."
                ),
            )
            if not approved:
                return
            self.service.delete_client(client_id)
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc))


class ClientDialog(QDialog):
    def __init__(self, parent=None, client=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Client" if client else "New Client")
        self.setMinimumWidth(460)

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        self.name_input = QLineEdit(client.full_name if client else "")
        self.name_input.setPlaceholderText("Full name")
        layout.addRow("Name *", self.name_input)

        self.phone_input = QLineEdit(client.phone if client else "")
        self.phone_input.setPlaceholderText("+1 555 123 45 67")
        layout.addRow("Phone *", self.phone_input)

        self.notes_input = QTextEdit(client.notes if client else "")
        self.notes_input.setMaximumHeight(90)
        self.notes_input.setPlaceholderText("Client notes")
        layout.addRow("Notes", self.notes_input)

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
            "phone": self.phone_input.text().strip(),
            "notes": self.notes_input.toPlainText().strip(),
        }
