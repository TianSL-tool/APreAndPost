import sys

from PySide6.QtWidgets import QApplication, QMainWindow
import multiprocessing  # 1. 导入multiprocessing模块（必须在主块外）
from mainwindow.ui_mainwindow import MainWindow


if __name__ == "__main__":
    # freeze_support()放在最开头，解决Windows打包多进程窗口问题
    multiprocessing.freeze_support()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())