import sys
import traceback

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QMessageBox

from database.connection import init_db
from views.main_window import MainWindow


def install_exception_hook() -> None:
    default_hook = sys.excepthook

    def _hook(exc_type, exc_value, exc_traceback):
        traceback_text = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(traceback_text, file=sys.stderr)
        QMessageBox.critical(
            None,
            "Unexpected Error",
            "An unexpected error occurred. Check terminal logs for technical details.",
        )
        default_hook(exc_type, exc_value, exc_traceback)

    sys.excepthook = _hook


def main() -> None:
    init_db()

    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 10))
    app.setStyle("Fusion")

    install_exception_hook()

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
