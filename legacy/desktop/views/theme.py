APP_STYLESHEET = """
QMainWindow {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f7fbff, stop:1 #eef3f8);
}

QStatusBar {
    background: #ffffff;
    border-top: 1px solid #d9dee8;
    color: #334155;
}

QTabWidget::pane {
    border: 1px solid #d9dee8;
    background: transparent;
    border-radius: 10px;
    top: -1px;
}

QTabBar::tab {
    background: #e7edf5;
    color: #334155;
    border: 1px solid #ced5e2;
    border-bottom: none;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 10px 16px;
    min-width: 128px;
    font-size: 13px;
    margin-right: 6px;
}

QTabBar::tab:selected {
    background: #ffffff;
    color: #0f172a;
    font-weight: 700;
}

QTabBar::tab:hover {
    background: #f0f5fb;
}

QLabel#PageTitle {
    font-size: 24px;
    font-weight: 700;
    color: #0f172a;
}

QLabel#PageSubtitle {
    font-size: 13px;
    color: #64748b;
    margin-bottom: 6px;
}

QTableWidget {
    background: #ffffff;
    color: #0f172a;
    gridline-color: #ebeff5;
    border: 1px solid #d9dee8;
    border-radius: 10px;
    selection-background-color: #dbeafe;
    selection-color: #0f172a;
}

QTableWidget::item {
    padding: 7px;
}

QHeaderView::section {
    background: #f8fafc;
    color: #475569;
    border: 0;
    border-bottom: 1px solid #d9dee8;
    padding: 9px;
    font-weight: 600;
}

QPushButton {
    background: #2563eb;
    color: white;
    border: none;
    border-radius: 9px;
    padding: 8px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background: #1d4ed8;
}

QPushButton:pressed {
    background: #1e40af;
}

QPushButton[variant="danger"] {
    background: #dc2626;
}

QPushButton[variant="danger"]:hover {
    background: #b91c1c;
}

QPushButton[variant="ghost"] {
    background: #ffffff;
    color: #334155;
    border: 1px solid #cbd5e1;
}

QPushButton[variant="ghost"]:hover {
    background: #f8fafc;
}

QLineEdit,
QTextEdit,
QComboBox,
QSpinBox,
QDoubleSpinBox,
QDateEdit {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #cbd5e1;
    border-radius: 9px;
    padding: 8px 10px;
}

QLineEdit:focus,
QTextEdit:focus,
QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus,
QDateEdit:focus {
    border: 1px solid #60a5fa;
}

QComboBox QAbstractItemView {
    background: #ffffff;
    color: #0f172a;
    selection-background-color: #dbeafe;
}

QLabel {
    color: #334155;
}

QGroupBox {
    color: #475569;
    border: 1px solid #d9dee8;
    border-radius: 10px;
    margin-top: 12px;
    padding-top: 16px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 6px;
}
"""
