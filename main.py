"""Entry point for TahaAi Visualizer (Python / PySide6 edition).

Run with:  python main.py
Build a standalone executable with:  pyinstaller build.spec
"""
import sys

from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("TahaAi Visualizer")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
