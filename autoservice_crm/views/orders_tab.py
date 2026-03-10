from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from models.work_order import STATUS_COMPLETED, STATUS_LABELS
from services.client_service import ClientService
from services.employee_service import EmployeeService
from services.errors import DomainError
from services.order_service import OrderService
from services.vehicle_service import VehicleService
from views.ui_utils import ask_confirm, busy_cursor, render_table, show_error, show_info


class OrdersTab(QWidget):
    def __init__(self):
        super().__init__()
        self.service = OrderService()
        self.client_service = ClientService()
        self.vehicle_service = VehicleService()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by order id, client or vehicle")
        self.search_input.textChanged.connect(self.refresh)
        top.addWidget(self.search_input)

        btn_add = QPushButton("Create Work Order")
        btn_add.clicked.connect(self._on_add)
        top.addWidget(btn_add)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Created", "Client", "Vehicle", "Status", "Total"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 160)
        self.table.setColumnWidth(4, 130)
        self.table.setColumnWidth(5, 130)
        self.table.doubleClicked.connect(self._on_open)
        layout.addWidget(self.table)

        bottom = QHBoxLayout()
        bottom.addStretch()

        btn_open = QPushButton("Open")
        btn_open.setProperty("variant", "ghost")
        btn_open.clicked.connect(self._on_open)
        bottom.addWidget(btn_open)

        btn_delete = QPushButton("Delete")
        btn_delete.setProperty("variant", "danger")
        btn_delete.clicked.connect(self._on_delete)
        bottom.addWidget(btn_delete)
        layout.addLayout(bottom)

    def refresh(self) -> None:
        search = self.search_input.text().strip() if hasattr(self, "search_input") else ""
        with busy_cursor():
            orders = self.service.list_orders(search)

        def build_row(row: int) -> None:
            order = orders[row]
            self.table.setItem(row, 0, QTableWidgetItem(str(order.id)))
            self.table.setItem(row, 1, QTableWidgetItem(order.created_at))
            self.table.setItem(row, 2, QTableWidgetItem(order.client_name))
            self.table.setItem(row, 3, QTableWidgetItem(order.vehicle_name))
            self.table.setItem(row, 4, QTableWidgetItem(order.status_label))
            self.table.setItem(row, 5, QTableWidgetItem(f"{order.total_amount:,.2f}"))

        render_table(self.table, len(orders), build_row)

    def _get_selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _on_add(self) -> None:
        clients = self.client_service.list_clients()
        if not clients:
            QMessageBox.warning(self, "Clients Required", "Create a client before creating work orders.")
            return
        dialog = OrderCreateDialog(self, clients, self.vehicle_service)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.create_order(**dialog.get_data())
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc))

    def _on_open(self) -> None:
        order_id = self._get_selected_id()
        if not order_id:
            QMessageBox.warning(self, "Selection", "Select a work order in the table.")
            return
        dialog = OrderDetailDialog(self, order_id)
        dialog.exec()
        self.refresh()

    def _on_delete(self) -> None:
        order_id = self._get_selected_id()
        if not order_id:
            QMessageBox.warning(self, "Selection", "Select a work order in the table.")
            return
        if not ask_confirm(
            self,
            "Confirm Delete",
            "Delete selected work order and all related work items?",
        ):
            return
        try:
            self.service.delete_order(order_id)
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc))


class OrderCreateDialog(QDialog):
    def __init__(self, parent, clients, vehicle_service: VehicleService):
        super().__init__(parent)
        self.vehicle_service = vehicle_service
        self.setWindowTitle("New Work Order")
        self.setMinimumWidth(500)

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        self.client_combo = QComboBox()
        for client in clients:
            self.client_combo.addItem(client.full_name, client.id)
        self.client_combo.currentIndexChanged.connect(self._update_vehicles)
        layout.addRow("Client *", self.client_combo)

        self.vehicle_combo = QComboBox()
        layout.addRow("Vehicle *", self.vehicle_combo)

        self.status_combo = QComboBox()
        for key, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, key)
        layout.addRow("Status", self.status_combo)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        self.notes_input.setPlaceholderText("Optional notes")
        layout.addRow("Notes", self.notes_input)

        actions = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setProperty("variant", "ghost")
        btn_cancel.clicked.connect(self.reject)
        actions.addWidget(btn_cancel)

        btn_save = QPushButton("Create")
        btn_save.clicked.connect(self._on_save)
        actions.addWidget(btn_save)
        layout.addRow(actions)

        self._update_vehicles()

    def _update_vehicles(self) -> None:
        self.vehicle_combo.clear()
        client_id = self.client_combo.currentData()
        if not client_id:
            return
        vehicles = self.vehicle_service.list_by_client(client_id)
        if not vehicles:
            self.vehicle_combo.addItem("No vehicles for selected client", None)
            return
        for v in vehicles:
            self.vehicle_combo.addItem(v.display_name, v.id)

    def _on_save(self) -> None:
        if not self.vehicle_combo.currentData():
            QMessageBox.warning(self, "Vehicle Required", "Selected client has no vehicles.")
            return
        self.accept()

    def get_data(self) -> dict:
        return {
            "client_id": self.client_combo.currentData(),
            "vehicle_id": self.vehicle_combo.currentData(),
            "status": self.status_combo.currentData(),
            "notes": self.notes_input.toPlainText().strip(),
        }


class OrderDetailDialog(QDialog):
    def __init__(self, parent, order_id: int):
        super().__init__(parent)
        self.order_id = order_id
        self.order_service = OrderService()
        self.client_service = ClientService()
        self.vehicle_service = VehicleService()
        self.employee_service = EmployeeService()

        self.setWindowTitle(f"Work Order #{order_id}")
        self.setMinimumSize(760, 620)
        self._build_ui()
        self._refresh_state()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        self.info_group = QGroupBox("Summary")
        info_layout = QGridLayout()
        self.info_order = QLabel()
        self.info_date = QLabel()
        self.info_client = QLabel()
        self.info_vehicle = QLabel()
        info_layout.addWidget(self.info_order, 0, 0)
        info_layout.addWidget(self.info_date, 0, 1)
        info_layout.addWidget(self.info_client, 1, 0)
        info_layout.addWidget(self.info_vehicle, 1, 1)
        self.info_group.setLayout(info_layout)
        layout.addWidget(self.info_group)

        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Status:"))
        self.status_combo = QComboBox()
        for key, label in STATUS_LABELS.items():
            self.status_combo.addItem(label, key)
        status_row.addWidget(self.status_combo)

        btn_status = QPushButton("Update Status")
        btn_status.clicked.connect(self._update_status)
        status_row.addWidget(btn_status)
        status_row.addStretch()

        self.total_label = QLabel()
        self.total_label.setStyleSheet("font-size: 18px; font-weight: 700; color: #047857;")
        status_row.addWidget(self.total_label)
        layout.addLayout(status_row)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(4)
        self.items_table.setHorizontalHeaderLabels(["Work", "Price", "Employee", ""])
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.setColumnWidth(1, 120)
        self.items_table.setColumnWidth(2, 210)
        self.items_table.setColumnWidth(3, 56)
        layout.addWidget(self.items_table)

        add_group = QGroupBox("Add Work Item")
        add_layout = QHBoxLayout()
        self.wi_name = QLineEdit()
        self.wi_name.setPlaceholderText("Work item name")
        add_layout.addWidget(self.wi_name, 3)

        self.wi_price = QDoubleSpinBox()
        self.wi_price.setRange(0, 1_000_000)
        self.wi_price.setDecimals(2)
        self.wi_price.setSingleStep(100)
        add_layout.addWidget(self.wi_price, 1)

        self.wi_employee = QComboBox()
        self.wi_employee.addItem("No employee", None)
        for emp in self.employee_service.list_employees():
            self.wi_employee.addItem(f"{emp.full_name} ({emp.commission_pct}%)", emp.id)
        add_layout.addWidget(self.wi_employee, 2)

        self.btn_add_item = QPushButton("Add")
        self.btn_add_item.clicked.connect(self._add_work_item)
        add_layout.addWidget(self.btn_add_item)
        add_group.setLayout(add_layout)
        layout.addWidget(add_group)

        close_btn = QPushButton("Close")
        close_btn.setProperty("variant", "ghost")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _refresh_state(self) -> None:
        try:
            with busy_cursor():
                order = self.order_service.get_order(self.order_id)
                client = self.client_service.get_client(order.client_id)
                vehicle = self.vehicle_service.get_vehicle(order.vehicle_id)
                items = self.order_service.list_items(self.order_id)
        except DomainError as exc:
            show_error(self, str(exc))
            self.reject()
            return

        self.info_order.setText(f"<b>Order:</b> #{order.id}")
        self.info_date.setText(f"<b>Date:</b> {order.created_at or ''}")
        self.info_client.setText(f"<b>Client:</b> {client.full_name}")
        self.info_vehicle.setText(f"<b>Vehicle:</b> {vehicle.display_name}")
        self.total_label.setText(f"Total: {order.total_amount:,.2f}")

        idx = self.status_combo.findData(order.status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)

        is_completed = order.status == STATUS_COMPLETED
        self.wi_name.setEnabled(not is_completed)
        self.wi_price.setEnabled(not is_completed)
        self.wi_employee.setEnabled(not is_completed)
        self.btn_add_item.setEnabled(not is_completed)

        def build_row(row: int) -> None:
            item = items[row]
            self.items_table.setItem(row, 0, QTableWidgetItem(item.name))
            self.items_table.setItem(row, 1, QTableWidgetItem(f"{item.price:,.2f}"))
            self.items_table.setItem(row, 2, QTableWidgetItem(item.employee_name))
            btn = QPushButton("X")
            btn.setProperty("variant", "danger")
            btn.setFixedSize(30, 24)
            btn.setEnabled(not is_completed)
            btn.clicked.connect(lambda _=False, item_id=item.id: self._delete_item(item_id))
            self.items_table.setCellWidget(row, 3, btn)

        render_table(self.items_table, len(items), build_row)

    def _update_status(self) -> None:
        new_status = self.status_combo.currentData()
        try:
            self.order_service.update_status(self.order_id, new_status)
            self._refresh_state()
            show_info(self, "Order status updated.")
        except DomainError as exc:
            show_error(self, str(exc))
            self._refresh_state()

    def _add_work_item(self) -> None:
        try:
            self.order_service.add_work_item(
                order_id=self.order_id,
                name=self.wi_name.text().strip(),
                price=self.wi_price.value(),
                employee_id=self.wi_employee.currentData(),
            )
            self.wi_name.clear()
            self.wi_price.setValue(0)
            self._refresh_state()
        except DomainError as exc:
            show_error(self, str(exc))

    def _delete_item(self, item_id: int) -> None:
        if not ask_confirm(self, "Confirm Delete", "Delete selected work item?"):
            return
        try:
            self.order_service.delete_work_item(order_id=self.order_id, item_id=item_id)
            self._refresh_state()
        except DomainError as exc:
            show_error(self, str(exc))
