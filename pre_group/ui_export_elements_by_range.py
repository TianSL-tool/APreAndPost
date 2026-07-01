import math
import os
import tempfile
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from pre_group import pre


def _validate_bounds(bounds):
    """校验并规范化 (xmin, xmax, ymin, ymax, zmin, zmax)。"""
    if len(bounds) != 6:
        raise ValueError("范围必须包含 x、y、z 三个方向的最小值和最大值。")
    values = tuple(float(value) for value in bounds)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("范围值必须是有限数值。")
    for index, axis_name in enumerate(("x", "y", "z")):
        lower, upper = values[index * 2:index * 2 + 2]
        if lower > upper:
            raise ValueError(
                f"{axis_name} 方向最小值不能大于最大值：{lower} > {upper}"
            )
    return values


def select_elements_by_center(elements, bounds):
    """按闭区间形心范围筛选单元；不修改单元或节点的任何属性。"""
    xmin, xmax, ymin, ymax, zmin, zmax = _validate_bounds(bounds)
    return [
        element for element in elements
        if xmin <= element.center[0] <= xmax
        and ymin <= element.center[1] <= ymax
        and zmin <= element.center[2] <= zmax
    ]


def _referenced_nodes_in_original_order(nodes, elements):
    referenced_ids = {
        point.node_id for element in elements for point in element.points
    }
    return [node for node in nodes if node.node_id in referenced_ids]


def _write_grid_subset(filename, nodes, elements):
    """写出完整网格子集，不调用任何会重排编号或修改对象的方法。"""
    with open(filename, "w", encoding="utf-8", buffering=8 * 1024 * 1024) as file:
        file.write("node\n")
        for node in nodes:
            file.write(
                f"{node.node_id:8d} {node.x:16.10f} {node.y:16.10f} "
                f"{node.z:16.10f} {int(node.ux):8d} {int(node.uy):8d} "
                f"{int(node.uz):8d} {int(node.press):8d} {int(node.rx):8d} "
                f"{int(node.ry):8d} {int(node.rz):8d}\n"
            )
        file.write("end node\nelement\n")
        for element in elements:
            file.write(element.get_write_string() + "\n")
        file.write("end element\n")


def export_elements_by_range(input_filename, output_filename, bounds, overwrite=False):
    """按形心范围输出单元及引用节点，返回 (节点数, 单元数)。"""
    input_path = Path(input_filename).expanduser().resolve()
    output_path = Path(output_filename).expanduser().resolve()
    normalized_bounds = _validate_bounds(bounds)
    if not input_path.is_file():
        raise FileNotFoundError(f"输入网格文件不存在：{input_path}")
    if input_path == output_path:
        raise ValueError("输出文件不能与输入网格文件相同，以免覆盖原始网格。")
    if output_path.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在：{output_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    nodes, elements, _, _ = pre.read_grid_file(str(input_path))
    if not nodes or not elements:
        raise ValueError("输入文件中没有读取到有效的节点和单元。")
    selected_elements = select_elements_by_center(elements, normalized_bounds)
    if not selected_elements:
        raise ValueError("给定形心范围内没有单元，未生成输出文件。")
    selected_nodes = _referenced_nodes_in_original_order(nodes, selected_elements)

    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=output_path.parent, prefix=f".{output_path.name}.",
            suffix=".tmp", delete=False,
        ) as temporary_file:
            temporary_name = temporary_file.name
        _write_grid_subset(temporary_name, selected_nodes, selected_elements)
        os.replace(temporary_name, output_path)
        temporary_name = None
    finally:
        if temporary_name and os.path.exists(temporary_name):
            os.remove(temporary_name)
    return len(selected_nodes), len(selected_elements)
