from PySide6.QtWidgets import QMainWindow, QTabWidget

from views.clients_tab import ClientsTab
from views.employees_tab import EmployeesTab
from views.orders_tab import OrdersTab
from views.payroll_tab import PayrollTab
from views.theme import APP_STYLESHEET
from views.vehicles_tab import VehiclesTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AutoService CRM")
        self.setMinimumSize(1120, 720)
        self.resize(1320, 860)

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setDocumentMode(True)
        self.tabs.setMovable(False)

        self.clients_tab = ClientsTab()
        self.vehicles_tab = VehiclesTab()
        self.orders_tab = OrdersTab()
        self.employees_tab = EmployeesTab()
        self.payroll_tab = PayrollTab()

        self.tabs.addTab(self.clients_tab, "Клиенты")
        self.tabs.addTab(self.vehicles_tab, "Автомобили")
        self.tabs.addTab(self.orders_tab, "Заказ-наряды")
        self.tabs.addTab(self.employees_tab, "Сотрудники")
        self.tabs.addTab(self.payroll_tab, "Зарплаты")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.setCentralWidget(self.tabs)
        self.statusBar().showMessage("Готово", 3000)
        self.setStyleSheet(APP_STYLESHEET)

    def _on_tab_changed(self, index: int) -> None:
        widget = self.tabs.widget(index)
        if hasattr(widget, "refresh"):
            widget.refresh()
