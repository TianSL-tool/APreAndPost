from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from pre_group import pre


def set_all_fill_ids(elements, fill_id):
    """Set the fill ID (c_id) of every element to one value."""
    fill_id = int(fill_id)
    if fill_id < 0:
        raise ValueError("\u586b\u7b51\u53f7\u4e0d\u80fd\u4e3a\u8d1f\u6570")

    changed_count = 0
    for element in elements:
        if element.c_id != fill_id:
            element.c_id = fill_id
            changed_count += 1
    return changed_count


def change_all_fill_ids(input_filename, output_filename, fill_id, overwrite=False):
    """Read a mesh, set every fill ID, and write it to a different file."""
    input_path = Path(input_filename).expanduser().resolve()
    output_path = Path(output_filename).expanduser().resolve()

    if input_path == output_path:
        raise ValueError("\u8f93\u5165\u6587\u4ef6\u4e0e\u8f93\u51fa\u6587\u4ef6\u4e0d\u80fd\u76f8\u540c\uff0c\u8bf7\u4f7f\u7528\u65b0\u7684\u8f93\u51fa\u6587\u4ef6\u540d")
    if not input_path.is_file():
        raise FileNotFoundError(f"\u8f93\u5165\u7f51\u683c\u6587\u4ef6\u4e0d\u5b58\u5728\uff1a{input_path}")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"\u8f93\u51fa\u6587\u4ef6\u5df2\u5b58\u5728\uff1a{output_path}")

    nodes, elements, _, _ = pre.read_grid_file(str(input_path))
    changed_count = set_all_fill_ids(elements, fill_id)
    pre.write_grid_file_02(str(output_path), nodes, elements)
    return len(elements), changed_count


class Ui_ChangeAllFillId(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("\u7edf\u4e00\u6240\u6709\u586b\u7b51\u53f7")
        self.resize(520, 180)

        self.input_edit = QLineEdit("Inimesh.dat")
        self.output_edit = QLineEdit("out_Inimesh.dat")
        self.fill_id_spin = QSpinBox()
        self.fill_id_spin.setRange(0, 2_147_483_647)

        input_button = QPushButton("\u6d4f\u89c8\u2026")
        output_button = QPushButton("\u6d4f\u89c8\u2026")
        input_button.clicked.connect(self._select_input_file)
        output_button.clicked.connect(self._select_output_file)

        input_layout = QHBoxLayout()
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(input_button)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(output_button)

        form_layout = QFormLayout()
        form_layout.addRow("\u8f93\u5165\u7f51\u683c\u6587\u4ef6\uff1a", input_layout)
        form_layout.addRow("\u7edf\u4e00\u586b\u7b51\u53f7\uff1a", self.fill_id_spin)
        form_layout.addRow("\u8f93\u51fa\u7f51\u683c\u6587\u4ef6\uff1a", output_layout)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form_layout)
        layout.addWidget(self.button_box)

    def _select_input_file(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "\u9009\u62e9\u8f93\u5165\u7f51\u683c\u6587\u4ef6",
            self.input_edit.text(),
            "DAT \u6587\u4ef6 (*.dat);;\u6240\u6709\u6587\u4ef6 (*)",
        )
        if filename:
            self.input_edit.setText(filename)

    def _select_output_file(self):
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "\u9009\u62e9\u8f93\u51fa\u7f51\u683c\u6587\u4ef6",
            self.output_edit.text(),
            "DAT \u6587\u4ef6 (*.dat);;\u6240\u6709\u6587\u4ef6 (*)",
        )
        if filename:
            self.output_edit.setText(filename)

    def ui_change_all_fill_id(self):
        input_filename = self.input_edit.text().strip()
        output_filename = self.output_edit.text().strip()
        fill_id = self.fill_id_spin.value()

        if not input_filename or not output_filename:
            QMessageBox.warning(self, "\u53c2\u6570\u9519\u8bef", "\u8f93\u5165\u6587\u4ef6\u548c\u8f93\u51fa\u6587\u4ef6\u4e0d\u80fd\u4e3a\u7a7a")
            return 0

        input_path = Path(input_filename).expanduser().resolve()
        output_path = Path(output_filename).expanduser().resolve()
        if input_path == output_path:
            QMessageBox.warning(
                self,
                "\u7981\u6b62\u8986\u76d6\u8f93\u5165\u6587\u4ef6",
                "\u8f93\u5165\u6587\u4ef6\u4e0e\u8f93\u51fa\u6587\u4ef6\u4e0d\u80fd\u76f8\u540c\uff0c\u8bf7\u6307\u5b9a\u65b0\u7684\u8f93\u51fa\u6587\u4ef6",
            )
            return 0

        overwrite = False
        if output_path.exists():
            answer = QMessageBox.question(
                self,
                "\u786e\u8ba4\u8986\u76d6",
                f"\u8f93\u51fa\u6587\u4ef6\u5df2\u5b58\u5728\uff1a\n{output_path}\n\n\u662f\u5426\u8986\u76d6\uff1f",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return 0
            overwrite = True

        try:
            total_count, changed_count = change_all_fill_ids(
                input_path, output_path, fill_id, overwrite=overwrite
            )
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "\u5904\u7406\u5931\u8d25", str(error))
            return 0

        QMessageBox.information(
            self,
            "\u5904\u7406\u5b8c\u6210",
            f"\u5355\u5143\u603b\u6570\uff1a{total_count}\n\u5b9e\u9645\u4fee\u6539\uff1a{changed_count}\n\u7edf\u4e00\u586b\u7b51\u53f7\uff1a{fill_id}",
        )
        return 1