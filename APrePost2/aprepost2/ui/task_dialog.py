from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from aprepost2.ui.task_catalog import TaskSpec


class TaskDialog(QDialog):
    def __init__(self, task: TaskSpec, parent=None):
        super().__init__(parent)
        self.task = task
        self.values: dict | None = None
        self.setWindowTitle(task.title)
        self.setMinimumWidth(620)

        description = QLabel(task.description)
        description.setWordWrap(True)
        description.setObjectName("description")

        self.editors: dict[str, QLineEdit] = {}
        self.overwrite_checkbox = None
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        for field in task.fields:
            editor = QLineEdit(field.default)
            self.editors[field.name] = editor
            if field.kind in {"open", "save", "directory"}:
                row = QHBoxLayout()
                row.addWidget(editor)
                browse = QPushButton("浏览…")
                browse.clicked.connect(
                    lambda checked=False, item=field: self._browse(item)
                )
                row.addWidget(browse)
                form.addRow(field.label + "：", row)
            else:
                form.addRow(field.label + "：", editor)
        if task.supports_overwrite:
            self.overwrite_checkbox = QCheckBox("允许覆盖已存在的输出文件")
            form.addRow("输出策略：", self.overwrite_checkbox)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_values)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(description)
        layout.addSpacing(8)
        layout.addLayout(form)
        layout.addSpacing(8)
        layout.addWidget(buttons)

    def _browse(self, field) -> None:
        current = self.editors[field.name].text()
        if field.kind == "open":
            filename, _ = QFileDialog.getOpenFileName(
                self, field.label, current, field.file_filter
            )
        elif field.kind == "directory":
            filename = QFileDialog.getExistingDirectory(self, field.label, current)
        else:
            filename, _ = QFileDialog.getSaveFileName(
                self, field.label, current, field.file_filter
            )
        if filename:
            self.editors[field.name].setText(filename)

    def _accept_values(self) -> None:
        values: dict = {}
        try:
            for field in self.task.fields:
                text = self.editors[field.name].text().strip()
                if not text:
                    raise ValueError(f"{field.label}不能为空")
                if field.kind == "int":
                    values[field.name] = int(text)
                elif field.kind == "float":
                    values[field.name] = float(text)
                else:
                    values[field.name] = text
        except ValueError as error:
            QMessageBox.warning(self, "参数错误", str(error))
            return

        overwrite = bool(
            self.overwrite_checkbox and self.overwrite_checkbox.isChecked()
        )
        if self.task.supports_overwrite:
            output = next(
                (
                    values[field.name]
                    for field in self.task.fields
                    if field.kind == "save"
                ),
                None,
            )
            if output and Path(output).expanduser().exists():
                answer = QMessageBox.question(
                    self,
                    "确认覆盖",
                    f"输出文件已存在：\n{Path(output).expanduser().resolve()}\n\n是否覆盖？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
                overwrite = True
            values["overwrite"] = overwrite
        self.values = values
        self.accept()
