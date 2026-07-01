from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from pre_group.ui_export_elements_by_range import (
    _validate_bounds,
    export_elements_by_range,
)


class ExportElementsByRangeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("按范围输出单元")
        self.resize(560, 330)
        self.export_result = None
        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        file_group = QGroupBox("文件")
        file_layout = QFormLayout(file_group)
        self.input_edit = QLineEdit("Inimesh.dat")
        self.output_edit = QLineEdit("range_elements.dat")
        file_layout.addRow("输入网格文件：", self._path_row(self.input_edit, False))
        file_layout.addRow("输出网格文件：", self._path_row(self.output_edit, True))
        main_layout.addWidget(file_group)

        range_group = QGroupBox("单元形心范围（闭区间）")
        range_layout = QGridLayout(range_group)
        range_layout.addWidget(QLabel("方向"), 0, 0)
        range_layout.addWidget(QLabel("最小值"), 0, 1)
        range_layout.addWidget(QLabel("最大值"), 0, 2)
        self.bound_edits = []
        for row, axis_name in enumerate(("x", "y", "z"), start=1):
            minimum_edit, maximum_edit = QLineEdit(), QLineEdit()
            minimum_edit.setPlaceholderText(f"{axis_name}_min")
            maximum_edit.setPlaceholderText(f"{axis_name}_max")
            range_layout.addWidget(QLabel(axis_name), row, 0)
            range_layout.addWidget(minimum_edit, row, 1)
            range_layout.addWidget(maximum_edit, row, 2)
            self.bound_edits.extend((minimum_edit, maximum_edit))
        main_layout.addWidget(range_group)

        note = QLabel(
            "输出包含范围内单元及其引用节点；不重编号，不改变单元类型、材料号、"
            "填筑号、节点连接顺序或节点约束。"
        )
        note.setWordWrap(True)
        main_layout.addWidget(note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._export)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

    def _path_row(self, line_edit, save_file):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(line_edit)
        button = QPushButton("浏览…")
        callback = self._select_output_file if save_file else self._select_input_file
        button.clicked.connect(lambda: callback(line_edit))
        layout.addWidget(button)
        return container

    def _select_input_file(self, line_edit):
        filename, _ = QFileDialog.getOpenFileName(
            self, "选择输入网格文件", line_edit.text(),
            "网格文件 (*.dat);;所有文件 (*)"
        )
        if filename:
            line_edit.setText(filename)

    def _select_output_file(self, line_edit):
        filename, _ = QFileDialog.getSaveFileName(
            self, "选择输出网格文件", line_edit.text(),
            "网格文件 (*.dat);;所有文件 (*)"
        )
        if filename:
            line_edit.setText(filename)

    def _export(self):
        input_filename = self.input_edit.text().strip()
        output_filename = self.output_edit.text().strip()
        if not input_filename or not output_filename:
            QMessageBox.warning(self, "参数错误", "输入和输出文件名不能为空。")
            return
        try:
            bounds = tuple(float(edit.text().strip()) for edit in self.bound_edits)
            _validate_bounds(bounds)
        except ValueError as error:
            QMessageBox.warning(self, "范围错误", f"请填写六个有效范围值。\n{error}")
            return

        output_path = Path(output_filename).expanduser().resolve()
        overwrite = False
        if output_path.exists():
            answer = QMessageBox.question(
                self, "确认覆盖", f"输出文件已存在：\n{output_path}\n\n是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            overwrite = True
        try:
            node_count, element_count = export_elements_by_range(
                input_filename, output_filename, bounds, overwrite=overwrite
            )
        except Exception as error:
            QMessageBox.critical(self, "输出失败", str(error))
            return
        self.export_result = (node_count, element_count, str(output_path))
        self.accept()
