from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.client_service import ClientService
from services.errors import DomainError
from services.vehicle_catalog import get_models_for_make, get_popular_makes
from services.vehicle_service import VehicleService
from services.vin_lookup_service import VinLookupService
from views.ui_utils import ask_confirm, busy_cursor, render_table, show_error, show_info


class VehiclesTab(QWidget):
    def __init__(self):
        super().__init__()
        self.service = VehicleService()
        self.client_service = ClientService()
        self._build_ui()
        self.refresh()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("Автомобили")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        subtitle = QLabel("Управляйте карточками авто, VIN и владельцами в одном месте.")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(subtitle)

        top = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск: владелец, марка, модель, VIN, госномер")
        self.search_input.textChanged.connect(self.refresh)
        top.addWidget(self.search_input)

        btn_add = QPushButton("Добавить автомобиль")
        btn_add.clicked.connect(self._on_add)
        top.addWidget(btn_add)
        layout.addLayout(top)

        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Марка", "Модель", "VIN", "Госномер", "Год", "Владелец"]
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setColumnWidth(0, 60)
        self.table.setColumnWidth(1, 130)
        self.table.setColumnWidth(5, 90)
        layout.addWidget(self.table)

        bottom = QHBoxLayout()
        bottom.addStretch()

        btn_edit = QPushButton("Редактировать")
        btn_edit.setProperty("variant", "ghost")
        btn_edit.clicked.connect(self._on_edit)
        bottom.addWidget(btn_edit)

        btn_delete = QPushButton("Удалить")
        btn_delete.setProperty("variant", "danger")
        btn_delete.clicked.connect(self._on_delete)
        bottom.addWidget(btn_delete)

        layout.addLayout(bottom)

    def refresh(self) -> None:
        search = self.search_input.text().strip() if hasattr(self, "search_input") else ""
        with busy_cursor():
            vehicles = self.service.list_vehicles(search)

        def build_row(row: int) -> None:
            vehicle = vehicles[row]
            self.table.setItem(row, 0, QTableWidgetItem(str(vehicle.id)))
            self.table.setItem(row, 1, QTableWidgetItem(vehicle.make))
            self.table.setItem(row, 2, QTableWidgetItem(vehicle.model))
            self.table.setItem(row, 3, QTableWidgetItem(vehicle.vin or "—"))
            self.table.setItem(row, 4, QTableWidgetItem(vehicle.license_plate or "—"))
            self.table.setItem(row, 5, QTableWidgetItem(str(vehicle.year) if vehicle.year else "—"))
            self.table.setItem(row, 6, QTableWidgetItem(vehicle.owner_name))

        render_table(self.table, len(vehicles), build_row)

    def _get_selected_id(self) -> int | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return int(item.text()) if item else None

    def _on_add(self) -> None:
        clients = self.client_service.list_clients()
        if not clients:
            QMessageBox.warning(self, "Нужны клиенты", "Сначала добавьте клиента.")
            return
        dialog = VehicleDialog(self, clients=clients)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.service.create_vehicle(**dialog.get_data())
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc))

    def _on_edit(self) -> None:
        vehicle_id = self._get_selected_id()
        if not vehicle_id:
            QMessageBox.warning(self, "Выбор", "Выберите автомобиль в таблице.")
            return
        try:
            vehicle = self.service.get_vehicle(vehicle_id)
            clients = self.client_service.list_clients()
            dialog = VehicleDialog(self, vehicle=vehicle, clients=clients)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self.service.update_vehicle(vehicle_id, **dialog.get_data())
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc))

    def _on_delete(self) -> None:
        vehicle_id = self._get_selected_id()
        if not vehicle_id:
            QMessageBox.warning(self, "Выбор", "Выберите автомобиль в таблице.")
            return
        try:
            vehicle = self.service.get_vehicle(vehicle_id)
            if not ask_confirm(
                self,
                "Подтверждение",
                (
                    f"Удалить автомобиль «{vehicle.display_name}»?\n\n"
                    "Связанные заказ-наряды и работы тоже будут удалены."
                ),
            ):
                return
            self.service.delete_vehicle(vehicle_id)
            self.refresh()
        except DomainError as exc:
            show_error(self, str(exc))


class VehicleDialog(QDialog):
    def __init__(self, parent=None, vehicle=None, clients=None):
        super().__init__(parent)
        self.vin_service = VinLookupService()
        self.setWindowTitle("Редактировать авто" if vehicle else "Новый автомобиль")
        self.setMinimumWidth(560)

        layout = QFormLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        self.client_combo = QComboBox()
        for client in clients or []:
            self.client_combo.addItem(client.full_name, client.id)
        if vehicle:
            idx = self.client_combo.findData(vehicle.client_id)
            if idx >= 0:
                self.client_combo.setCurrentIndex(idx)
        layout.addRow("Владелец *", self.client_combo)

        vin_row = QHBoxLayout()
        self.vin_input = QLineEdit(vehicle.vin if vehicle else "")
        self.vin_input.setPlaceholderText("17 символов VIN")
        vin_row.addWidget(self.vin_input)
        btn_decode = QPushButton("Определить по VIN")
        btn_decode.setProperty("variant", "ghost")
        btn_decode.clicked.connect(self._on_decode_vin)
        vin_row.addWidget(btn_decode)
        layout.addRow("VIN", vin_row)

        self.make_combo = QComboBox()
        self.make_combo.setEditable(True)
        self.make_combo.addItems(get_popular_makes())
        self.make_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.make_combo.lineEdit().setPlaceholderText("Выберите или введите марку")
        self.make_combo.currentTextChanged.connect(self._on_make_changed)
        self._attach_completer(self.make_combo, get_popular_makes())
        layout.addRow("Марка *", self.make_combo)

        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.model_combo.lineEdit().setPlaceholderText("Выберите или введите модель")
        layout.addRow("Модель *", self.model_combo)

        self.plate_input = QLineEdit(vehicle.license_plate if vehicle else "")
        self.plate_input.setPlaceholderText("A123BC777")
        layout.addRow("Госномер", self.plate_input)

        self.year_input = QSpinBox()
        self.year_input.setRange(0, datetime.now().year + 1)
        self.year_input.setSpecialValueText("—")
        self.year_input.setValue(vehicle.year if vehicle and vehicle.year else 0)
        layout.addRow("Год", self.year_input)

        initial_make = vehicle.make if vehicle else ""
        initial_model = vehicle.model if vehicle else ""
        self.make_combo.setEditText(initial_make)
        self._refresh_model_options(initial_make, preferred_model=initial_model)
        if initial_model:
            self.model_combo.setEditText(initial_model)

        actions = QHBoxLayout()
        btn_cancel = QPushButton("Отмена")
        btn_cancel.setProperty("variant", "ghost")
        btn_cancel.clicked.connect(self.reject)
        actions.addWidget(btn_cancel)

        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self.accept)
        actions.addWidget(btn_save)
        layout.addRow(actions)

    def _attach_completer(self, combo: QComboBox, values: list[str]) -> None:
        completer = QCompleter(values, combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        combo.setCompleter(completer)

    def _on_make_changed(self, make: str) -> None:
        self._refresh_model_options(make, preferred_model=self.model_combo.currentText().strip())

    def _refresh_model_options(self, make: str, preferred_model: str = "") -> None:
        models = get_models_for_make(make)
        current = preferred_model or self.model_combo.currentText().strip()
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        if models:
            self.model_combo.addItems(models)
            self._attach_completer(self.model_combo, models)
        else:
            self._attach_completer(self.model_combo, [])
        self.model_combo.blockSignals(False)
        if current:
            self.model_combo.setEditText(current)

    def _on_decode_vin(self) -> None:
        vin = self.vin_input.text().strip()
        try:
            with busy_cursor():
                decoded = self.vin_service.decode(vin)
        except DomainError as exc:
            show_error(self, str(exc), title="VIN ошибка")
            return

        self.vin_input.setText(decoded.vin)
        self.make_combo.setEditText(decoded.make)
        self._refresh_model_options(decoded.make, preferred_model=decoded.model)
        if decoded.model:
            self.model_combo.setEditText(decoded.model)
        if decoded.model_year:
            self.year_input.setValue(decoded.model_year)

        warning_part = f"\n\n{decoded.warning}" if decoded.warning else ""
        model_text = decoded.model if decoded.model else "модель не определена"
        show_info(
            self,
            f"Определено: {decoded.make} {model_text}, {decoded.model_year or 'год не указан'}{warning_part}",
            title="VIN распознан",
        )

    def get_data(self) -> dict:
        year = self.year_input.value()
        return {
            "client_id": self.client_combo.currentData(),
            "make": self.make_combo.currentText().strip(),
            "model": self.model_combo.currentText().strip(),
            "vin": self.vin_input.text().strip(),
            "license_plate": self.plate_input.text().strip(),
            "year": year if year > 0 else None,
        }
