from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from aprepost2.services.common import OperationResult
from aprepost2.ui.task_catalog import TASKS, TASK_BY_KEY
from aprepost2.ui.task_dialog import TaskDialog
from aprepost2.ui.workers import FunctionWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("APrePost 2 — 岩土工程前后处理")
        self.resize(1080, 720)
        self.thread_pool = QThreadPool.globalInstance()
        self.active_workers: set[FunctionWorker] = set()
        self.current_task_key: str | None = None
        self._build_ui()
        self._build_menu()
        self._apply_style()

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(18, 18, 18, 12)

        title = QLabel("APrePost 2")
        title.setObjectName("appTitle")
        subtitle = QLabel("模块化网格前处理、计算结果读取与反演后处理")
        subtitle.setObjectName("subtitle")
        root_layout.addWidget(title)
        root_layout.addWidget(subtitle)
        root_layout.addSpacing(12)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.task_tree = QTreeWidget()
        self.task_tree.setHeaderHidden(True)
        self.task_tree.setMinimumWidth(280)
        self.task_tree.itemSelectionChanged.connect(self._selection_changed)
        self.task_tree.itemDoubleClicked.connect(lambda *_: self._open_current_task())

        categories: dict[str, QTreeWidgetItem] = {}
        for task in TASKS:
            parent = categories.get(task.category)
            if parent is None:
                parent = QTreeWidgetItem([task.category])
                parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                categories[task.category] = parent
                self.task_tree.addTopLevelItem(parent)
            child = QTreeWidgetItem([task.title])
            child.setData(0, Qt.ItemDataRole.UserRole, task.key)
            parent.addChild(child)
        self.task_tree.expandAll()

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(22, 8, 8, 8)
        self.task_title = QLabel("请选择一项功能")
        self.task_title.setObjectName("taskTitle")
        self.task_description = QLabel("左侧列出了原程序主界面的全部功能。")
        self.task_description.setWordWrap(True)
        self.run_button = QPushButton("配置并运行")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self._open_current_task)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setPlaceholderText("任务状态、输出文件和错误详情会显示在这里。")
        detail_layout.addWidget(self.task_title)
        detail_layout.addWidget(self.task_description)
        detail_layout.addSpacing(8)
        detail_layout.addWidget(self.run_button, 0, Qt.AlignmentFlag.AlignLeft)
        detail_layout.addSpacing(10)
        detail_layout.addWidget(QLabel("运行日志"))
        detail_layout.addWidget(self.log, 1)

        splitter.addWidget(self.task_tree)
        splitter.addWidget(detail)
        splitter.setStretchFactor(1, 1)
        root_layout.addWidget(splitter, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        self.status_label = QLabel("就绪")
        self.progress = QProgressBar()
        self.progress.setFixedWidth(180)
        self.progress.setVisible(False)
        status.addWidget(self.status_label, 1)
        status.addPermanentWidget(self.progress)

    def _build_menu(self) -> None:
        for category in ("前处理", "后处理"):
            menu = self.menuBar().addMenu(category)
            for task in (item for item in TASKS if item.category == category):
                action = QAction(task.title, self)
                action.triggered.connect(
                    lambda checked=False, key=task.key: self._open_task(key)
                )
                menu.addAction(action)
        help_menu = self.menuBar().addMenu("帮助")
        about = QAction("关于", self)
        about.triggered.connect(
            lambda: QMessageBox.information(
                self,
                "关于 APrePost 2",
                "APrePost 2\n模块化岩土工程前后处理程序\n\n"
                "计算结果用于工程分析时，请结合原始数据和专业判断进行复核。",
            )
        )
        help_menu.addAction(about)

    def _selection_changed(self) -> None:
        items = self.task_tree.selectedItems()
        if not items:
            return
        key = items[0].data(0, Qt.ItemDataRole.UserRole)
        if not key:
            return
        task = TASK_BY_KEY[key]
        self.current_task_key = key
        self.task_title.setText(task.title)
        self.task_description.setText(task.description)
        self.run_button.setEnabled(True)

    def _open_current_task(self) -> None:
        if self.current_task_key:
            self._open_task(self.current_task_key)

    def _open_task(self, key: str) -> None:
        task = TASK_BY_KEY[key]
        dialog = TaskDialog(task, self)
        if dialog.exec() != TaskDialog.DialogCode.Accepted or dialog.values is None:
            return
        self._start_worker(task, dialog.values)

    def _start_worker(self, task, values: dict) -> None:
        worker = FunctionWorker(task.handler, values)
        self.active_workers.add(worker)
        worker.signals.succeeded.connect(self._task_succeeded)
        worker.signals.failed.connect(self._task_failed)
        worker.signals.finished.connect(lambda item=worker: self._task_finished(item))
        self.status_label.setText(f"正在运行：{task.title}")
        self.progress.setRange(0, 0)
        self.progress.setVisible(True)
        self.run_button.setEnabled(False)
        self._append_log(f"开始：{task.title}")
        self.thread_pool.start(worker)

    def _task_succeeded(self, result: OperationResult) -> None:
        self._append_log(result.message)
        for path in result.output_paths:
            self._append_log(f"输出：{path}")
        QMessageBox.information(self, result.title, result.message)

    def _task_failed(self, message: str, details: str) -> None:
        self._append_log(f"失败：{message}\n{details}")
        QMessageBox.warning(self, "处理失败", message)

    def _task_finished(self, worker: FunctionWorker) -> None:
        self.active_workers.discard(worker)
        if not self.active_workers:
            self.progress.setVisible(False)
            self.progress.setRange(0, 100)
            self.status_label.setText("就绪")
            self.run_button.setEnabled(self.current_task_key is not None)

    def _append_log(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.append(f"[{timestamp}] {text}")

    def _apply_style(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow { background: #f4f6f8; }
            QLabel#appTitle { font-size: 28px; font-weight: 700; color: #17324d; }
            QLabel#subtitle { font-size: 14px; color: #617387; }
            QLabel#taskTitle { font-size: 22px; font-weight: 650; color: #17324d; }
            QTreeWidget, QTextEdit {
                background: white; border: 1px solid #d8e0e8; border-radius: 7px;
            }
            QTreeWidget::item { min-height: 31px; padding-left: 5px; }
            QTreeWidget::item:selected { background: #d9eaf7; color: #12344d; }
            QPushButton {
                background: #176b87; color: white; border: 0; border-radius: 5px;
                padding: 8px 18px; font-weight: 600;
            }
            QPushButton:hover { background: #12566d; }
            QPushButton:disabled { background: #a9b7c2; }
            QStatusBar { background: white; border-top: 1px solid #d8e0e8; }
            """
        )
