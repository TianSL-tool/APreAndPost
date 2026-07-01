from __future__ import annotations

import multiprocessing
import sys

from PySide6.QtWidgets import QApplication

from aprepost2.ui.main_window import MainWindow


def main() -> int:
    multiprocessing.freeze_support()
    application = QApplication.instance() or QApplication(sys.argv)
    application.setApplicationName("APrePost 2")
    window = MainWindow()
    window.show()
    return application.exec()
