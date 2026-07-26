from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTreeView,
    QVBoxLayout,
)

from aprepost2.services.tecplot_merge import (
    discover_plt_files,
    infer_tecplot_step,
    group_tecplot_files_explicit,
    group_tecplot_step_files,
)


PLT_FILTER = "Tecplot ASCII 文件 (*.plt);;所有文件 (*)"


class PltStepMergeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.values: dict | None = None
        self._known_paths: set[str] = set()
        self.setWindowTitle("PLT 单步提取与合并")
        self.resize(920, 620)

        description = QLabel(
            "从多个 Tecplot ASCII .plt 文件中提取同一计算步的完整 Zone，"
            "按下表顺序合并到新文件。计算步按各文件内 Zone 的顺序从 1 开始计数。"
        )
        description.setWordWrap(True)

        instructions = QLabel(
            "配置说明（本功能无需制作控制文件）：\n"
            "1. 用“添加文件”“添加多个文件夹”或“递归扫描”加入待处理的 .plt 文件；\n"
            "2. 计算步是每个文件内 Zone 的顺序号，从 1 开始；\n"
            "3. 双击工况名称可修改标识，用上移/下移确定顺序；“复制工况”可让同一源文件多次出现；\n"
            "4. 文件夹中有多个不同名 .plt 时会全部展开，以完整路径区分，可按需移除；\n"
            "5. 指定新的输出 .plt 文件。程序会在写出前检查计算步和 VARIABLES 体系，"
            "原始文件不会被修改。"
        )
        instructions.setWordWrap(True)
        instructions.setObjectName("instructions")
        instructions.setStyleSheet(
            "QLabel#instructions {"
            "background: #eef6fb; border: 1px solid #c7dce9; border-radius: 5px;"
            "padding: 9px; color: #294b5f;"
            "}"
        )

        add_files = QPushButton("添加文件…")
        add_folders = QPushButton("添加多个文件夹…")
        add_recursive = QPushButton("递归扫描…")
        add_files.clicked.connect(self._add_files)
        add_folders.clicked.connect(self._add_folders)
        add_recursive.clicked.connect(self._add_recursive)
        source_buttons = QHBoxLayout()
        source_buttons.addWidget(add_files)
        source_buttons.addWidget(add_folders)
        source_buttons.addWidget(add_recursive)
        source_buttons.addStretch(1)

        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(("工况名称（可编辑）", "PLT 文件"))
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)

        move_up = QPushButton("上移")
        move_down = QPushButton("下移")
        copy_case = QPushButton("复制工况")
        remove = QPushButton("移除")
        clear = QPushButton("清空")
        move_up.clicked.connect(lambda: self._move_selected(-1))
        move_down.clicked.connect(lambda: self._move_selected(1))
        copy_case.clicked.connect(self._copy_selected)
        remove.clicked.connect(self._remove_selected)
        clear.clicked.connect(self._clear)
        order_buttons = QHBoxLayout()
        order_buttons.addWidget(move_up)
        order_buttons.addWidget(move_down)
        order_buttons.addWidget(copy_case)
        order_buttons.addWidget(remove)
        order_buttons.addWidget(clear)
        order_buttons.addStretch(1)

        self.step = QSpinBox()
        self.step.setRange(1, 2_147_483_647)
        self.step.setValue(1)
        self.output = QLineEdit("merged_step.plt")
        browse_output = QPushButton("浏览…")
        browse_output.clicked.connect(self._browse_output)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output)
        output_row.addWidget(browse_output)
        self.overwrite = QCheckBox("允许覆盖已存在的输出文件")
        form = QFormLayout()
        form.addRow("计算步（Zone 序号）：", self.step)
        form.addRow("输出 PLT：", output_row)
        form.addRow("输出策略：", self.overwrite)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_values)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(description)
        layout.addWidget(instructions)
        layout.addLayout(source_buttons)
        layout.addWidget(self.table, 1)
        layout.addLayout(order_buttons)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _add_files(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self, "添加 Tecplot ASCII 文件", "", PLT_FILTER
        )
        self._append_paths(Path(name) for name in filenames)

    def _select_multiple_directories(self) -> list[str]:
        dialog = QFileDialog(self, "选择一个或多个文件夹")
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
        dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
        for view in (*dialog.findChildren(QListView), *dialog.findChildren(QTreeView)):
            view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return []
        return dialog.selectedFiles()

    def _add_folders(self) -> None:
        directories = self._select_multiple_directories()
        if not directories:
            return
        try:
            paths = discover_plt_files(directories, recursive=False)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "扫描失败", str(error))
            return
        self._append_paths(paths)
        if not paths:
            QMessageBox.information(self, "未发现文件", "所选文件夹中没有 .plt 文件。")

    def _add_recursive(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择递归扫描根文件夹")
        if not directory:
            return
        try:
            paths = discover_plt_files((directory,), recursive=True)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "扫描失败", str(error))
            return
        self._append_paths(paths)
        if not paths:
            QMessageBox.information(
                self, "未发现文件", "所选文件夹及其子文件夹中没有 .plt 文件。"
            )

    def _unique_case_name(self, path: Path) -> str:
        used = {
            self.table.item(row, 0).text().strip()
            for row in range(self.table.rowCount())
            if self.table.item(row, 0)
        }
        base = path.stem
        if base not in used:
            return base
        folder_based = f"{base}（{path.parent.name}）"
        if folder_based not in used:
            return folder_based
        index = 2
        while f"{folder_based}-{index}" in used:
            index += 1
        return f"{folder_based}-{index}"

    def _unique_copy_name(self, source_name: str) -> str:
        used = {
            self.table.item(row, 0).text().strip()
            for row in range(self.table.rowCount())
            if self.table.item(row, 0)
        }
        base = f"{source_name}（副本）"
        if base not in used:
            return base
        index = 2
        while f"{source_name}（副本{index}）" in used:
            index += 1
        return f"{source_name}（副本{index}）"

    def _insert_entry(self, row: int, case_name: str, path: Path) -> None:
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(case_name))
        path_item = QTableWidgetItem(str(path))
        path_item.setFlags(path_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        self.table.setItem(row, 1, path_item)

    def _append_paths(self, paths) -> None:
        for path_value in paths:
            path = Path(path_value).expanduser().resolve()
            identity = os.path.normcase(str(path))
            if identity in self._known_paths:
                continue
            row = self.table.rowCount()
            self._insert_entry(row, self._unique_case_name(path), path)
            self._known_paths.add(identity)

    def _swap_rows(self, first: int, second: int) -> None:
        for column in range(self.table.columnCount()):
            first_item = self.table.takeItem(first, column)
            second_item = self.table.takeItem(second, column)
            self.table.setItem(first, column, second_item)
            self.table.setItem(second, column, first_item)

    def _move_selected(self, direction: int) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if len(rows) != 1:
            QMessageBox.information(self, "调整顺序", "请只选择一个工况后再上移或下移。")
            return
        row = rows[0]
        target = row + direction
        if target < 0 or target >= self.table.rowCount():
            return
        self._swap_rows(row, target)
        self.table.selectRow(target)

    def _copy_selected(self) -> None:
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not rows:
            QMessageBox.information(self, "复制工况", "请先选择一个或多个工况。")
            return
        copied_rows: list[int] = []
        offset = 0
        for original_row in rows:
            source_row = original_row + offset
            name = self.table.item(source_row, 0).text().strip()
            path = Path(self.table.item(source_row, 1).text())
            target_row = source_row + 1
            self._insert_entry(target_row, self._unique_copy_name(name), path)
            copied_rows.append(target_row)
            offset += 1
        self.table.clearSelection()
        for row in copied_rows:
            self.table.selectRow(row)

    def _rebuild_known_paths(self) -> None:
        self._known_paths = {
            os.path.normcase(self.table.item(row, 1).text())
            for row in range(self.table.rowCount())
            if self.table.item(row, 1)
        }

    def _remove_selected(self) -> None:
        rows = sorted(
            {index.row() for index in self.table.selectedIndexes()}, reverse=True
        )
        for row in rows:
            self.table.removeRow(row)
        self._rebuild_known_paths()

    def _clear(self) -> None:
        self.table.setRowCount(0)
        self._known_paths.clear()

    def _browse_output(self) -> None:
        filename, _ = QFileDialog.getSaveFileName(
            self, "输出合并 PLT", self.output.text(), PLT_FILTER
        )
        if filename:
            self.output.setText(filename)

    def _accept_values(self) -> None:
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "参数错误", "请至少添加一个 .plt 文件。")
            return
        files = [self.table.item(row, 1).text() for row in range(self.table.rowCount())]
        names = [
            self.table.item(row, 0).text().strip()
            for row in range(self.table.rowCount())
        ]
        if any(not name for name in names):
            QMessageBox.warning(self, "参数错误", "工况名称不能为空。")
            return
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            QMessageBox.warning(
                self, "参数错误", "工况名称不能重复：" + "、".join(duplicates)
            )
            return
        output_text = self.output.text().strip()
        if not output_text:
            QMessageBox.warning(self, "参数错误", "输出 PLT 不能为空。")
            return
        output = Path(output_text).expanduser().resolve()
        if os.path.normcase(str(output)) in {
            os.path.normcase(str(Path(path).resolve())) for path in files
        }:
            QMessageBox.warning(
                self, "输出路径错误", "输出文件不能与任何输入文件相同。"
            )
            return
        overwrite = self.overwrite.isChecked()
        if output.exists():
            answer = QMessageBox.question(
                self,
                "确认覆盖",
                f"输出文件已存在：\n{output}\n\n是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            overwrite = True
        self.values = {
            "input_files": files,
            "case_names": names,
            "step": self.step.value(),
            "output_path": str(output),
            "overwrite": overwrite,
        }
        self.accept()



class PltSeriesMergeDialog(QDialog):
    """Edit file-to-output grouping and calculation steps before merging."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.values: dict | None = None
        self._known_paths: set[str] = set()
        self.setWindowTitle("\u6309\u8ba1\u7b97\u6b65\u5408\u5e76 PLT")
        self.resize(960, 620)

        description = QLabel(
            "\u6bcf\u4e2a PLT \u6587\u4ef6\u5360\u4e00\u884c\u3002"
            "\u5206\u7ec4\u8f93\u51fa\u540d\u548c\u8ba1\u7b97\u6b65\u5747\u53ef\u53cc\u51fb\u7f16\u8f91\uff1b"
            "\u540c\u4e00\u8f93\u51fa\u540d\u7684\u6587\u4ef6\u5c06\u6309\u6570\u503c\u6b65\u53f7\u5408\u5e76\u3002"
        )
        description.setWordWrap(True)

        add_files = QPushButton("\u6dfb\u52a0\u6587\u4ef6\u2026")
        add_folder = QPushButton("\u6dfb\u52a0\u6587\u4ef6\u5939\u2026")
        add_recursive = QPushButton("\u9012\u5f52\u6dfb\u52a0\u2026")
        remove = QPushButton("\u79fb\u9664\u9009\u4e2d")
        clear = QPushButton("\u6e05\u7a7a")
        add_files.clicked.connect(self._add_files)
        add_folder.clicked.connect(lambda: self._add_directory(False))
        add_recursive.clicked.connect(lambda: self._add_directory(True))
        remove.clicked.connect(self._remove_selected)
        clear.clicked.connect(self._clear)
        source_buttons = QHBoxLayout()
        for button in (add_files, add_folder, add_recursive, remove, clear):
            source_buttons.addWidget(button)
        source_buttons.addStretch(1)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ("\u5206\u7ec4\u8f93\u51fa\u540d\uff08\u53ef\u7f16\u8f91\uff09",
             "\u8ba1\u7b97\u6b65\uff08\u53ef\u7f16\u8f91\uff09",
             "PLT \u6587\u4ef6")
        )
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setColumnWidth(0, 290)
        self.table.setColumnWidth(1, 150)
        self.table.setSortingEnabled(True)
        self.table.sortItems(0, Qt.SortOrder.AscendingOrder)

        self.summary_table = QTableWidget(0, 4)
        self.summary_table.setHorizontalHeaderLabels(
            ("\u5206\u7ec4\u8f93\u51fa\u540d", "\u8ba1\u7b97\u6b65\u987a\u5e8f", "\u6587\u4ef6\u6570", "\u6700\u7ec8\u6587\u4ef6")
        )
        self.summary_table.horizontalHeader().setStretchLastSection(True)
        self.summary_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setMaximumHeight(180)
        self.table.itemChanged.connect(self._refresh_summary)

        self.output_directory = QLineEdit()
        output_button = QPushButton("\u6d4f\u89c8\u2026")
        output_button.clicked.connect(self._browse_output_directory)
        output_row = QHBoxLayout()
        output_row.addWidget(self.output_directory)
        output_row.addWidget(output_button)
        self.overwrite = QCheckBox("\u5141\u8bb8\u8986\u76d6\u5df2\u6709\u5408\u5e76\u7ed3\u679c")
        form = QFormLayout()
        form.addRow("\u5408\u5e76\u7ed3\u679c\u6587\u4ef6\u5939\uff1a", output_row)
        form.addRow("\u8f93\u51fa\u7b56\u7565\uff1a", self.overwrite)

        note = QLabel(
            "\u81ea\u52a8\u8bc6\u522b\u793a\u4f8b\uff1a result_12.plt\u3001result-12.plt "
            "\u548c result12.plt \u90fd\u53ef\u63a8\u65ad\u6b65\u53f7 12\u3002"
            "\u6587\u4ef6\u540d\u672b\u5c3e\u6ca1\u6709\u6570\u5b57\u7684 .plt \u6587\u4ef6\u4e0d\u8ba1\u5165\u3002"
            "\u82e5\u63a8\u65ad\u4e0d\u7b26\u5408\u5b9e\u9645\uff0c\u76f4\u63a5\u5728\u8868\u683c\u4e2d\u4fee\u6539\u3002"
        )
        note.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_values)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(description)
        layout.addLayout(source_buttons)
        layout.addWidget(self.table, 1)
        summary_header = QHBoxLayout()
        summary_header.addWidget(QLabel("\u5408\u5e76\u6c47\u603b"))
        refresh_summary = QPushButton("\u66f4\u65b0\u6c47\u603b")
        refresh_summary.clicked.connect(self._refresh_summary)
        summary_header.addWidget(refresh_summary)
        summary_header.addStretch(1)
        layout.addLayout(summary_header)
        layout.addWidget(self.summary_table)
        layout.addLayout(form)
        layout.addWidget(note)
        layout.addWidget(buttons)

    def _add_files(self) -> None:
        filenames, _ = QFileDialog.getOpenFileNames(
            self, "\u6dfb\u52a0 Tecplot PLT", "", PLT_FILTER
        )
        self._append_paths(Path(name) for name in filenames)

    def _add_directory(self, recursive: bool) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "\u9009\u62e9 PLT \u6587\u4ef6\u5939"
        )
        if not directory:
            return
        try:
            paths = discover_plt_files((directory,), recursive=recursive)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "\u626b\u63cf\u5931\u8d25", str(error))
            return
        self._append_paths(paths)
        if not paths:
            QMessageBox.information(self, "\u672a\u53d1\u73b0\u6587\u4ef6", "\u6ca1\u6709\u627e\u5230 .plt \u6587\u4ef6\u3002")

    def _append_paths(self, paths) -> None:
        first_parent: Path | None = None
        sorting_enabled = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        for value in paths:
            path = Path(value).expanduser().resolve()
            identity = os.path.normcase(str(path))
            if identity in self._known_paths:
                continue
            inferred = infer_tecplot_step(path)
            if inferred is None:
                continue
            name, step = inferred
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(row, 1, QTableWidgetItem(str(step)))
            path_item = QTableWidgetItem(str(path))
            path_item.setFlags(path_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, path_item)
            self._known_paths.add(identity)
            first_parent = first_parent or path.parent
        self.table.setSortingEnabled(sorting_enabled)
        if sorting_enabled:
            self.table.sortItems(0, Qt.SortOrder.AscendingOrder)
        if first_parent is not None and not self.output_directory.text().strip():
            self.output_directory.setText(str(first_parent))
        self._refresh_summary()

    def _remove_selected(self) -> None:
        rows = sorted(
            {index.row() for index in self.table.selectedIndexes()}, reverse=True
        )
        for row in rows:
            item = self.table.item(row, 2)
            if item:
                self._known_paths.discard(os.path.normcase(item.text()))
            self.table.removeRow(row)

    def _clear(self) -> None:
        self.table.setRowCount(0)
        self._known_paths.clear()

    def _refresh_summary(self, *_args) -> None:
        grouped: dict[str, list[str]] = {}
        display_names: dict[str, str] = {}
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            step_item = self.table.item(row, 1)
            path_item = self.table.item(row, 2)
            if not name_item or not step_item or not path_item:
                continue
            name = name_item.text().strip()
            if not name:
                continue
            identity = name.casefold()
            display_names.setdefault(identity, name)
            grouped.setdefault(identity, []).append(step_item.text().strip())

        self.summary_table.setRowCount(0)
        for identity in sorted(grouped):
            values = grouped[identity]
            try:
                ordered = [str(value) for value in sorted(int(item) for item in values)]
            except ValueError:
                ordered = values
            name = display_names[identity]
            row = self.summary_table.rowCount()
            self.summary_table.insertRow(row)
            summary = (name, ", ".join(ordered), str(len(values)), f"{name}_merged.plt")
            for column, value in enumerate(summary):
                self.summary_table.setItem(row, column, QTableWidgetItem(value))
    def _browse_output_directory(self) -> None:
        directory = QFileDialog.getExistingDirectory(
            self, "\u9009\u62e9\u5408\u5e76\u7ed3\u679c\u6587\u4ef6\u5939"
        )
        if directory:
            self.output_directory.setText(directory)

    def _accept_values(self) -> None:
        if self.table.rowCount() < 2:
            QMessageBox.warning(self, "\u53c2\u6570\u9519\u8bef", "\u8bf7\u81f3\u5c11\u6dfb\u52a0\u4e24\u4e2a PLT \u6587\u4ef6\u3002")
            return
        output_text = self.output_directory.text().strip()
        if not output_text:
            QMessageBox.warning(self, "\u53c2\u6570\u9519\u8bef", "\u8bf7\u9009\u62e9\u5408\u5e76\u7ed3\u679c\u6587\u4ef6\u5939\u3002")
            return

        files = [self.table.item(row, 2).text() for row in range(self.table.rowCount())]
        names = [self.table.item(row, 0).text().strip() for row in range(self.table.rowCount())]
        step_texts = [self.table.item(row, 1).text().strip() for row in range(self.table.rowCount())]
        try:
            steps = [int(value) for value in step_texts]
            groups = group_tecplot_files_explicit(files, names, steps)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "\u5206\u7ec4\u6216\u6b65\u53f7\u9519\u8bef", str(error))
            return

        output = Path(output_text).expanduser().resolve()
        existing = [
            output / f"{group.name}_merged.plt"
            for group in groups
            if (output / f"{group.name}_merged.plt").exists()
        ]
        overwrite = self.overwrite.isChecked()
        if existing and not overwrite:
            answer = QMessageBox.question(
                self,
                "\u786e\u8ba4\u8986\u76d6",
                "\u5df2\u6709\u5408\u5e76\u7ed3\u679c\u5c06\u88ab\u8986\u76d6\uff1a\n"
                + "\n".join(map(str, existing))
                + "\n\n\u662f\u5426\u7ee7\u7eed\uff1f",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            overwrite = True

        self.values = {
            "input_files": files,
            "output_names": names,
            "steps": steps,
            "output_directory": str(output),
            "overwrite": overwrite,
        }
        self.accept()
