from __future__ import annotations

import math
from pathlib import Path

from aprepost2.domain import BaseElement, Mesh, replace_element_type
from aprepost2.io.mesh_io import read_mesh, write_mesh
from aprepost2.io.text import clean_control_lines
from aprepost2.services.common import OperationResult, checked_paths


def _parse_counted_pairs(path: str | Path) -> dict[int, int]:
    lines = clean_control_lines(path)
    if not lines:
        raise ValueError("控制文件为空")
    count = int(lines[0].split()[0])
    if len(lines) < count + 1:
        raise ValueError(f"控制文件声明 {count} 组映射，但数据行不足")
    mapping: dict[int, int] = {}
    for index, line in enumerate(lines[1 : count + 1], 1):
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(f"第 {index} 组映射必须包含旧值和新值")
        old_value, new_value = map(int, parts)
        if old_value < 0 or new_value < 0:
            raise ValueError("编号不能为负数")
        if old_value in mapping:
            raise ValueError(f"旧编号 {old_value} 重复定义")
        mapping[old_value] = new_value
    return mapping


def _write_modified(
    input_path: str,
    output_path: str,
    mutate,
    *,
    overwrite: bool,
    title: str,
) -> OperationResult:
    source, target = checked_paths(input_path, output_path)
    mesh = read_mesh(source)
    changed = int(mutate(mesh))
    write_mesh(target, mesh, overwrite=overwrite)
    return OperationResult(
        title,
        f"处理完成：共 {len(mesh.elements)} 个单元，修改 {changed} 项。",
        (target,),
        {"nodes": len(mesh.nodes), "elements": len(mesh.elements), "changed": changed},
    )


def remap_material_ids(
    input_path: str, control_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    mapping = _parse_counted_pairs(control_path)
    return _write_modified(
        input_path,
        output_path,
        lambda mesh: _remap(mesh, "m_id", mapping),
        overwrite=overwrite,
        title="材料号修改",
    )


def remap_fill_ids(
    input_path: str, control_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    mapping = _parse_counted_pairs(control_path)
    return _write_modified(
        input_path,
        output_path,
        lambda mesh: _remap(mesh, "c_id", mapping),
        overwrite=overwrite,
        title="填筑号修改",
    )


def _remap(mesh: Mesh, attribute: str, mapping: dict[int, int]) -> int:
    changed = 0
    for element in mesh.elements:
        current = getattr(element, attribute)
        replacement = mapping.get(current)
        if replacement is not None and replacement != current:
            setattr(element, attribute, replacement)
            changed += 1
    return changed


def change_all_fill_ids(
    input_path: str, output_path: str, fill_id: int, *, overwrite: bool = False
) -> OperationResult:
    fill_id = int(fill_id)
    if fill_id < 0:
        raise ValueError("填筑号不能为负数")
    return _write_modified(
        input_path,
        output_path,
        lambda mesh: _set_all(mesh, "c_id", fill_id),
        overwrite=overwrite,
        title="统一填筑号",
    )


def _set_all(mesh: Mesh, attribute: str, value: int) -> int:
    changed = 0
    for element in mesh.elements:
        if getattr(element, attribute) != value:
            setattr(element, attribute, value)
            changed += 1
    return changed


def change_element_types(
    input_path: str, control_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    lines = clean_control_lines(control_path)
    if not lines:
        raise ValueError("控制文件为空")
    material_count = int(lines.pop(0).split()[0])
    if len(lines) < material_count + 1:
        raise ValueError("控制文件中的材料号或类型映射数据不足")
    materials = {int(lines.pop(0).split()[0]) for _ in range(material_count)}
    pair_count = int(lines.pop(0).split()[0])
    if len(lines) < pair_count:
        raise ValueError("控制文件中的单元类型映射数据不足")
    type_mapping: dict[int, int] = {}
    for line in lines[:pair_count]:
        parts = line.split()
        if len(parts) != 2:
            raise ValueError("每组单元类型映射必须包含旧类型和新类型")
        old_type, new_type = map(int, parts)
        type_mapping[old_type] = new_type

    def mutate(mesh: Mesh) -> int:
        changed = 0
        for index, element in enumerate(mesh.elements):
            new_type = type_mapping.get(element.t_id)
            if element.m_id not in materials or new_type is None:
                continue
            if element.t_id == 6 and new_type == 61:
                if len(element.node_ids) < 8 or len(set(element.node_ids[3:8])) != 1:
                    continue
            mesh.elements[index] = replace_element_type(element, new_type)
            changed += 1
        return changed

    return _write_modified(
        input_path,
        output_path,
        mutate,
        overwrite=overwrite,
        title="单元类型修改",
    )


def add_pore_constraints(
    input_path: str, control_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    material_pairs = tuple(_parse_counted_pairs(control_path).items())

    def mutate(mesh: Mesh) -> int:
        node_materials: dict[int, set[int]] = {}
        for element in mesh.elements:
            material = element.m_id
            for node_id in element.node_ids:
                node_materials.setdefault(node_id, set()).add(material)
        changed = 0
        for node in mesh.nodes:
            materials = node_materials.get(node.node_id, ())
            if node.press != 1 and any(
                first in materials and second in materials
                for first, second in material_pairs
            ):
                node.press = 1
                changed += 1
        return changed

    return _write_modified(
        input_path,
        output_path,
        mutate,
        overwrite=overwrite,
        title="添加孔压约束",
    )


def _read_scale_control(path: str | Path):
    values: dict[str, str] = {}
    for line in clean_control_lines(path):
        if "=" not in line:
            raise ValueError(f"缩放控制行缺少 '='：{line}")
        key, value = line.split("=", 1)
        values[key.strip().upper()] = value.strip()
    required = {
        "BASE_POINT",
        "SCALE_DIR",
        "SCALE_RANGE_MIN",
        "SCALE_RANGE_MAX",
        "SCALE_FACTOR",
    }
    missing = required - values.keys()
    if missing:
        raise ValueError(f"缩放控制文件缺少参数：{', '.join(sorted(missing))}")
    base = tuple(float(value) for value in values["BASE_POINT"].replace(",", " ").split())
    if len(base) != 3:
        raise ValueError("BASE_POINT 必须包含三个坐标")
    direction = values["SCALE_DIR"].lower()
    if direction not in {"x", "y", "z"}:
        raise ValueError("SCALE_DIR 只能是 x、y 或 z")
    lower = float(values["SCALE_RANGE_MIN"])
    upper = float(values["SCALE_RANGE_MAX"])
    factor = float(values["SCALE_FACTOR"])
    if lower >= upper:
        raise ValueError("缩放范围最小值必须小于最大值")
    if factor <= 0 or not math.isfinite(factor):
        raise ValueError("缩放系数必须为有限正数")
    return base, direction, lower, upper, factor


def scale_coordinates(
    input_path: str, control_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    base, direction, lower, upper, factor = _read_scale_control(control_path)

    def mutate(mesh: Mesh) -> int:
        axis = {"x": 0, "y": 1, "z": 2}[direction]
        base_coordinate = base[axis]
        new_lower = base_coordinate + (lower - base_coordinate) * factor
        new_upper = base_coordinate + (upper - base_coordinate) * factor
        changed = 0
        for node in mesh.nodes:
            coordinate = getattr(node, direction)
            if lower <= coordinate <= upper:
                new_coordinate = base_coordinate + (coordinate - base_coordinate) * factor
            elif coordinate < lower:
                new_coordinate = new_lower + coordinate - lower
            else:
                new_coordinate = new_upper + coordinate - upper
            if new_coordinate != coordinate:
                setattr(node, direction, new_coordinate)
                changed += 1
        mesh.invalidate_geometry_cache()
        return changed

    return _write_modified(
        input_path,
        output_path,
        mutate,
        overwrite=overwrite,
        title="节点坐标缩放",
    )


def export_elements_by_bounds(
    input_path: str,
    output_path: str,
    bounds: tuple[float, float, float, float, float, float],
    *,
    overwrite: bool = False,
) -> OperationResult:
    source, target = checked_paths(input_path, output_path)
    values = tuple(float(value) for value in bounds)
    if len(values) != 6 or not all(math.isfinite(value) for value in values):
        raise ValueError("范围必须包含六个有限数值")
    xmin, xmax, ymin, ymax, zmin, zmax = values
    if xmin > xmax or ymin > ymax or zmin > zmax:
        raise ValueError("任一方向的最小值均不能大于最大值")
    mesh = read_mesh(source)
    selected: list[BaseElement] = []
    referenced: set[int] = set()
    for element in mesh.elements:
        x, y, z = element.center(mesh.node_map)
        if xmin <= x <= xmax and ymin <= y <= ymax and zmin <= z <= zmax:
            selected.append(element)
            referenced.update(element.node_ids)
    if not selected:
        raise ValueError("给定形心范围内没有单元")
    selected_nodes = [node for node in mesh.nodes if node.node_id in referenced]
    write_mesh(
        target,
        mesh,
        nodes=selected_nodes,
        elements=selected,
        overwrite=overwrite,
    )
    return OperationResult(
        "按范围输出单元",
        f"已输出 {len(selected)} 个单元、{len(selected_nodes)} 个引用节点。",
        (target,),
        {"nodes": len(selected_nodes), "elements": len(selected)},
    )


def mesh_statistics(
    input_path: str,
    output_path: str,
    *,
    overwrite: bool = False,
) -> OperationResult:
    """统计网格的材料/单元类型分布及孔压节点，输出到 Excel。

    Count element distribution by material and type, node counts per
    category, and pore-pressure nodes; write results to Excel.
    """
    import pandas as pd

    source, target = checked_paths(input_path, output_path)
    mesh = read_mesh(source)

    # -- 按材料统计 / per-material stats --
    material_elements: dict[int, int] = {}
    material_nodes: dict[int, set[int]] = {}
    for element in mesh.elements:
        material_elements[element.m_id] = (
            material_elements.get(element.m_id, 0) + 1
        )
        material_nodes.setdefault(element.m_id, set()).update(element.node_ids)

    # -- 按单元类型统计 / per-type stats --
    type_elements: dict[int, int] = {}
    type_nodes: dict[int, set[int]] = {}
    for element in mesh.elements:
        type_elements[element.t_id] = (
            type_elements.get(element.t_id, 0) + 1
        )
        type_nodes.setdefault(element.t_id, set()).update(element.node_ids)

    # -- 孔压节点 / pore pressure nodes --
    pore_nodes = [node for node in mesh.nodes if node.press == 1]
    pore_node_ids = {node.node_id for node in pore_nodes}

    # -- 构建 DataFrame / build DataFrames --
    material_frame = pd.DataFrame(
        [
            {"material_id": m_id, "element_count": count,
             "node_count": len(material_nodes[m_id])}
            for m_id, count in sorted(material_elements.items())
        ]
    )
    type_frame = pd.DataFrame(
        [
            {"element_type": t_id, "element_count": count,
             "node_count": len(type_nodes[t_id])}
            for t_id, count in sorted(type_elements.items())
        ]
    )
    pore_frame = pd.DataFrame(
        [{"pore_pressure_node_count": len(pore_node_ids)}]
    )
    summary_frame = pd.DataFrame(
        [
            {
                "total_nodes": len(mesh.nodes),
                "total_elements": len(mesh.elements),
                "material_types": len(material_elements),
                "element_types": len(type_elements),
                "pore_pressure_nodes": len(pore_node_ids),
            }
        ]
    )

    # -- 写出 Excel / write Excel --
    target.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(target, engine="openpyxl") as writer:
        material_frame.to_excel(writer, sheet_name="材料统计", index=False)
        type_frame.to_excel(writer, sheet_name="单元类型统计", index=False)
        pore_frame.to_excel(writer, sheet_name="孔压节点", index=False)
        summary_frame.to_excel(writer, sheet_name="汇总", index=False)

    return OperationResult(
        "网格统计",
        f"统计完成：{len(mesh.nodes)} 个节点、{len(mesh.elements)} 个单元、"
        f"{len(material_elements)} 种材料、{len(type_elements)} 种单元类型、"
        f"{len(pore_node_ids)} 个孔压节点。",
        (target,),
        {
            "total_nodes": len(mesh.nodes),
            "total_elements": len(mesh.elements),
            "material_types": len(material_elements),
            "element_types": len(type_elements),
            "pore_nodes": len(pore_node_ids),
        },
    )


def _parse_material_list(path: str) -> list[int]:
    """解析材料列表控制文件，每行一个材料号。

    Parse a material list control file with one material ID per line.
    Format: <count> then <material_id> per line.
    """
    lines = clean_control_lines(path)
    if not lines:
        raise ValueError("控制文件为空")
    count = int(lines[0].split()[0])
    if count <= 0:
        raise ValueError("材料数量必须大于 0")
    if len(lines) < count + 1:
        raise ValueError(f"控制文件声明 {count} 个材料，但数据行不足")
    materials: list[int] = []
    for index, line in enumerate(lines[1 : count + 1], 1):
        parts = line.split()
        if not parts:
            raise ValueError(f"第 {index} 个材料的数据为空")
        m_id = int(parts[0])
        if m_id < 0:
            raise ValueError(f"第 {index} 个材料号不能为负数：{m_id}")
        materials.append(m_id)
    return materials


def export_element_mesh_by_material(
    input_path: str,
    control_path: str,
    output_path: str,
    *,
    overwrite: bool = False,
) -> OperationResult:
    """按材料分别输出单元网格，每种材料生成一个独立文件。

    Export element meshes by material — one file per material,
    each containing the elements of that material and their referenced nodes.

    Output files are named as {stem}_material_{m_id}{suffix}.
    """
    source = Path(input_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"输入文件不存在：{source}")

    material_ids = _parse_material_list(control_path)
    mesh = read_mesh(source)

    material_elements: dict[int, list[BaseElement]] = {}
    for element in mesh.elements:
        material_elements.setdefault(element.m_id, []).append(element)

    missing = [m_id for m_id in material_ids if m_id not in material_elements]
    if missing:
        raise ValueError(
            f"以下材料号在网格中不存在：{', '.join(str(m) for m in missing)}"
        )

    stem = target.stem
    suffix = target.suffix
    output_paths: list[Path] = []
    per_material_counts: dict[str, int] = {}

    for m_id in material_ids:
        elements = material_elements[m_id]
        referenced: set[int] = set()
        for element in elements:
            referenced.update(element.node_ids)
        selected_nodes = [
            node for node in mesh.nodes if node.node_id in referenced
        ]

        material_target = target.parent / f"{stem}_material_{m_id}{suffix}"
        if material_target == source:
            raise ValueError(
                f"材料 {m_id} 的输出路径与输入文件相同，请更换输出目录或基础文件名"
            )

        write_mesh(
            material_target,
            mesh,
            nodes=selected_nodes,
            elements=elements,
            overwrite=overwrite,
        )
        output_paths.append(material_target)
        per_material_counts[str(m_id)] = len(elements)

    total_elements = sum(per_material_counts.values())
    return OperationResult(
        "按材料输出单元网格",
        f"已完成 {len(material_ids)} 种材料的单元导出，"
        f"共输出 {total_elements} 个单元。",
        tuple(output_paths),
        {
            "material_count": len(material_ids),
            "total_elements": total_elements,
            **per_material_counts,
        },
    )
