from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QVBoxLayout,
)

from basemethod.base_method import read_and_clean_file
from pre_group import pre


def read_scale_by_center_config(config_file):
    """
    读取“以节点为中心缩放全部节点”的控制参数。

    支持两种写法：
    CENTER_NODE_ID = 100
    SCALE_FACTOR = 1.2

    或：
    CENTER_NODE_ID = 100
    SCALE_X = 1.2
    SCALE_Y = 1.0
    SCALE_Z = 0.8
    """
    cleaned_lines = read_and_clean_file(config_file)
    if not cleaned_lines:
        raise FileNotFoundError(f"控制文件 {config_file} 读取失败或为空")

    config = {}
    for line_num, line in enumerate(cleaned_lines, 1):
        if "=" not in line:
            raise ValueError(
                f"控制文件第 {line_num} 行格式错误：缺少 '='，"
                "示例：CENTER_NODE_ID = 100"
            )
        key, value = line.split("=", 1)
        config[key.strip().upper()] = value.strip()

    if "CENTER_NODE_ID" not in config:
        raise KeyError("控制文件缺少 CENTER_NODE_ID")

    center_node_id = int(config["CENTER_NODE_ID"])
    uniform_scale = float(config.get("SCALE_FACTOR", "1.0"))
    scale_x = float(config.get("SCALE_X", uniform_scale))
    scale_y = float(config.get("SCALE_Y", uniform_scale))
    scale_z = float(config.get("SCALE_Z", uniform_scale))

    scale_factors = (scale_x, scale_y, scale_z)
    if any(scale <= 0 for scale in scale_factors):
        raise ValueError(f"缩放系数必须大于 0，当前为 {scale_factors}")

    return center_node_id, scale_factors


def scale_nodes_by_center_node(nodes, node_map, center_node_id, scale_factors):
    """
    所有节点按指定中心节点坐标进行缩放。

    数学关系：
    x' = x_c + (x - x_c) * scale_x
    y' = y_c + (y - y_c) * scale_y
    z' = z_c + (z - z_c) * scale_z
    """
    if not nodes:
        raise ValueError("节点列表为空，无法缩放")
    if center_node_id not in node_map:
        raise ValueError(f"中心节点 {center_node_id} 不存在")
    if len(scale_factors) != 3:
        raise ValueError("scale_factors 必须包含 x/y/z 三个方向的缩放系数")

    scale_x, scale_y, scale_z = scale_factors
    center_node = node_map[center_node_id]
    center_x, center_y, center_z = center_node.x, center_node.y, center_node.z

    for node in nodes:
        node.x = center_x + (node.x - center_x) * scale_x
        node.y = center_y + (node.y - center_y) * scale_y
        node.z = center_z + (node.z - center_z) * scale_z

    return center_x, center_y, center_z


def scale_all_nodes_by_center_node(
    control_filename,
    in_mesh_filename,
    output_filename,
    overwrite=False,
):
    input_path = Path(in_mesh_filename)
    output_path = Path(output_filename)

    if input_path.resolve() == output_path.resolve():
        raise ValueError("输出文件不能与输入网格文件相同，避免覆盖原始输入文件")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在：{output_path}")

    center_node_id, scale_factors = read_scale_by_center_config(control_filename)
    nodes, elements, node_map, _ = pre.read_grid_file(in_mesh_filename)
    center = scale_nodes_by_center_node(
        nodes=nodes,
        node_map=node_map,
        center_node_id=center_node_id,
        scale_factors=scale_factors,
    )
    pre.write_grid_file_01(output_filename, nodes, elements)
    print(
        "全部节点缩放完成 | "
        f"中心节点：{center_node_id} | 中心坐标：{center} | "
        f"缩放系数：{scale_factors} | 输出文件：{output_filename}"
    )
    return len(nodes), len(elements), center_node_id, center, scale_factors


class UiScaleAllNodesByCenterNode(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("所有节点以节点为中心缩放")
        self.resize(360, 150)

        self.mesh_line_edit = QLineEdit("Inimesh.dat")
        self.control_line_edit = QLineEdit("control.dat")
        self.output_line_edit = QLineEdit("out_Inimesh.dat")
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )

        layout = QVBoxLayout(self)
        grid_layout = QGridLayout()
        grid_layout.addWidget(QLabel("网格文件："), 0, 0)
        grid_layout.addWidget(self.mesh_line_edit, 0, 1)
        grid_layout.addWidget(QLabel("控制文件："), 1, 0)
        grid_layout.addWidget(self.control_line_edit, 1, 1)
        grid_layout.addWidget(QLabel("输出文件："), 2, 0)
        grid_layout.addWidget(self.output_line_edit, 2, 1)
        layout.addLayout(grid_layout)
        layout.addWidget(self.button_box)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

    def ui_scale_all_nodes_by_center_node(self):
        input_filename = self.mesh_line_edit.text().strip()
        control_filename = self.control_line_edit.text().strip()
        output_filename = self.output_line_edit.text().strip()

        if not input_filename or not control_filename or not output_filename:
            raise ValueError("网格文件、控制文件和输出文件不能为空")

        output_path = Path(output_filename)
        overwrite = False
        if output_path.exists():
            reply = QMessageBox.question(
                self,
                "确认覆盖输出文件",
                f"输出文件已存在：\n{output_path}\n\n是否覆盖？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return 0
            overwrite = True

        scale_all_nodes_by_center_node(
            control_filename=control_filename,
            in_mesh_filename=input_filename,
            output_filename=output_filename,
            overwrite=overwrite,
        )
        return 1
