from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from aprepost2.domain import BaseElement, Mesh, create_element, element_response_type, replace_element_type
from aprepost2.domain.element import (
    EdgeStructured2D,
    Hexahedron,
    HigherOrder,
    HigherOrderHexahedron,
    HigherOrderWedge,
    HigherOrderWedgeAlt,
    PayloadFormat,
    PolygonSolid2D,
    Polyhedron,
    QuadSolid2D,
    QuadraticQuad2D,
    QuadraticTriangle2D,
)
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


def _offset_topology_payload(
    element: BaseElement, node_id_offset: int
) -> tuple[int, ...]:
    return _remap_topology_payload(
        element, lambda node_id: node_id + node_id_offset
    )


def _remap_topology_payload(element: BaseElement, remap) -> tuple[int, ...]:
    payload = element.topology_payload()
    payload_format = element.PAYLOAD_FORMAT
    if payload_format in {PayloadFormat.A, PayloadFormat.B, PayloadFormat.F}:
        metadata_count = 0
    elif payload_format == PayloadFormat.C:
        metadata_count = 1 + int(payload[0])
    elif payload_format == PayloadFormat.D:
        metadata_count = 1 + int(payload[0])
    elif payload_format == PayloadFormat.E:
        face_count = int(payload[0])
        metadata_count = 1 + face_count + sum(payload[1 : 1 + face_count])
    elif payload_format == PayloadFormat.G:
        metadata_count = int(type(element).PREAMBLE_SIZE)
    else:
        raise ValueError(
            f"单元 {element.e_id} 使用未知 Payload 格式：{payload_format}"
        )
    return (
        *payload[:metadata_count],
        *(remap(node_id) for node_id in payload[metadata_count:]),
    )


def offset_mesh_ids(
    input_path: str,
    node_id_offset: int,
    element_id_offset: int,
    output_path: str,
    *,
    overwrite: bool = False,
) -> OperationResult:
    """Apply independent uniform offsets to all node and element IDs."""
    source, target = checked_paths(input_path, output_path)
    node_id_offset = int(node_id_offset)
    element_id_offset = int(element_id_offset)
    mesh = read_mesh(source)

    if min(node.node_id for node in mesh.nodes) + node_id_offset < 0:
        raise ValueError("节点号偏移后不能小于 0")
    if min(element.e_id for element in mesh.elements) + element_id_offset < 0:
        raise ValueError("单元号偏移后不能小于 0")

    for node in mesh.nodes:
        node.node_id += node_id_offset
    shifted_elements = [
        create_element(
            element.e_id + element_id_offset,
            element.t_id,
            element.c_id,
            element.m_id,
            element.d_id,
            element.f_id,
            _offset_topology_payload(element, node_id_offset),
        )
        for element in mesh.elements
    ]
    shifted_mesh = Mesh(mesh.nodes, shifted_elements)
    shifted_mesh.validate_connectivity()
    write_mesh(target, shifted_mesh, overwrite=overwrite)
    return OperationResult(
        "节点/单元编号整体偏移",
        f"处理完成：{len(mesh.nodes)} 个节点的编号增加 {node_id_offset}，"
        f"{len(mesh.elements)} 个单元的编号增加 {element_id_offset}。",
        (target,),
        {
            "nodes": len(mesh.nodes),
            "elements": len(mesh.elements),
            "node_id_offset": node_id_offset,
            "element_id_offset": element_id_offset,
        },
    )


def merge_close_nodes(
    input_path: str,
    distance_tolerance: float,
    output_path: str,
    *,
    overwrite: bool = False,
) -> OperationResult:
    """Merge transitive groups of nodes whose pair distances are below a limit."""
    from scipy.sparse import coo_matrix
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree

    source, target = checked_paths(input_path, output_path)
    tolerance = float(distance_tolerance)
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise ValueError("合并距离必须是大于 0 的有限数")

    mesh = read_mesh(source)
    coordinates = mesh.coordinates_array()
    if not np.all(np.isfinite(coordinates)):
        raise ValueError("节点坐标中存在 NaN 或无穷值，无法执行距离合并")

    candidate_pairs = cKDTree(coordinates).query_pairs(
        tolerance, output_type="ndarray"
    )
    if candidate_pairs.size:
        deltas = coordinates[candidate_pairs[:, 0]] - coordinates[candidate_pairs[:, 1]]
        squared_distances = np.einsum("ij,ij->i", deltas, deltas)
        pairs = candidate_pairs[squared_distances < tolerance * tolerance]
    else:
        pairs = np.empty((0, 2), dtype=np.int64)

    node_count = len(mesh.nodes)
    if pairs.size:
        graph = coo_matrix(
            (
                np.ones(len(pairs), dtype=np.uint8),
                (pairs[:, 0], pairs[:, 1]),
            ),
            shape=(node_count, node_count),
        )
        group_count, labels = connected_components(
            graph, directed=False, return_labels=True
        )
    else:
        group_count = node_count
        labels = np.arange(node_count, dtype=np.int64)

    representative_indices = np.full(group_count, -1, dtype=np.int64)
    ordered_indices = sorted(
        range(node_count), key=lambda index: mesh.nodes[index].node_id
    )
    for index in ordered_indices:
        label = int(labels[index])
        if representative_indices[label] < 0:
            representative_indices[label] = index

    representative_by_index = representative_indices[labels]
    node_id_mapping = {
        node.node_id: mesh.nodes[int(representative_by_index[index])].node_id
        for index, node in enumerate(mesh.nodes)
    }
    constraint_fields = ("ux", "uy", "uz", "press", "rx", "ry", "rz")
    label_counts = np.bincount(labels, minlength=group_count)
    indices_by_label = np.argsort(labels, kind="stable")
    label_starts = np.concatenate(([0], np.cumsum(label_counts)))
    merged_labels = np.flatnonzero(label_counts > 1)
    for label in merged_labels:
        representative_index = representative_indices[label]
        member_indices = indices_by_label[
            label_starts[label] : label_starts[label + 1]
        ]
        representative = mesh.nodes[int(representative_index)]
        for field in constraint_fields:
            setattr(
                representative,
                field,
                max(getattr(mesh.nodes[int(index)], field) for index in member_indices),
            )

    kept_nodes = [
        node
        for index, node in enumerate(mesh.nodes)
        if int(representative_by_index[index]) == index
    ]
    remapped_elements: list[BaseElement] = []
    collapsed_elements = 0
    for element in mesh.elements:
        old_unique_count = len(set(element.node_ids))
        remapped = create_element(
            element.e_id,
            element.t_id,
            element.c_id,
            element.m_id,
            element.d_id,
            element.f_id,
            _remap_topology_payload(
                element, lambda node_id: node_id_mapping[node_id]
            ),
        )
        if len(set(remapped.node_ids)) < old_unique_count:
            collapsed_elements += 1
        remapped_elements.append(remapped)

    merged_mesh = Mesh(kept_nodes, remapped_elements)
    merged_mesh.validate_connectivity()
    write_mesh(target, merged_mesh, overwrite=overwrite)
    merged_nodes = node_count - len(kept_nodes)
    return OperationResult(
        "按距离合并节点",
        f"处理完成：{node_count} 个节点合并为 {len(kept_nodes)} 个，"
        f"删除 {merged_nodes} 个重复节点；"
        f"{collapsed_elements} 个单元的唯一连接节点数减少。",
        (target,),
        {
            "input_nodes": node_count,
            "output_nodes": len(kept_nodes),
            "merged_nodes": merged_nodes,
            "merge_groups": len(merged_labels),
            "neighbor_pairs": len(pairs),
            "collapsed_elements": collapsed_elements,
            "distance_tolerance": tolerance,
        },
    )


def change_element_types(
    input_path: str, control_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    materials, type_mapping = _parse_material_type_conversion_control(control_path)

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


# ---------------------------------------------------------------------------
# 按材料执行单元拓扑互转
# ---------------------------------------------------------------------------

def _parse_material_type_conversion_control(
    control_path: str | Path,
) -> tuple[set[int], dict[int, int]]:
    lines = clean_control_lines(control_path)
    if not lines:
        raise ValueError("控制文件为空")

    material_count = int(lines.pop(0).split()[0])
    if material_count < 0:
        raise ValueError(f"材料数量不能为负数：{material_count}")
    if len(lines) < material_count + 1:
        raise ValueError(
            f"材料号或类型映射行数不足：声明 {material_count} 个材料，"
            f"至少需要 {material_count + 1} 行（材料号 + 转换对数量），"
            f"实际剩余 {len(lines)} 行"
        )

    materials = {int(lines.pop(0).split()[0]) for _ in range(material_count)}
    pair_count_line = lines.pop(0)
    pair_count_parts = pair_count_line.split()
    if len(pair_count_parts) == 2:
        raise ValueError(
            f"应为转换对数量行，但读到两列数据 '{pair_count_line}'。"
            f"请在该行之前插入一行作为转换对数量（如 '1'），"
            f"当前剩余 {len(lines)} 行。"
            f"\n正确格式：材料数量 → 材料号… → 转换对数量 → 旧类型 新类型…"
        )
    pair_count = int(pair_count_parts[0])
    if pair_count < 0:
        raise ValueError(f"转换对数量不能为负数：{pair_count}")
    if len(lines) < pair_count:
        raise ValueError(
            f"单元类型映射行数不足：声明 {pair_count} 对映射，"
            f"实际只有 {len(lines)} 行。"
            f"\n正确格式：材料数量 → 材料号… → 转换对数量 → 旧类型 新类型…"
        )
    type_mapping: dict[int, int] = {}
    for index, line in enumerate(lines[:pair_count], 1):
        parts = line.split()
        if len(parts) != 2:
            raise ValueError(
                f"第 {index} 组单元类型映射必须恰好两列（旧类型 新类型），"
                f"当前为：'{line}'"
            )
        old_type, new_type = map(int, parts)
        if old_type in type_mapping:
            raise ValueError(f"旧类型 {old_type} 重复定义")
        type_mapping[old_type] = new_type
    return materials, type_mapping


def _copy_with_payload(
    element: BaseElement,
    target_t_id: int,
    payload: tuple[int, ...],
) -> BaseElement:
    return create_element(
        element.e_id,
        target_t_id,
        element.c_id,
        element.m_id,
        element.d_id,
        element.f_id,
        payload,
    )


def _quad_to_polygon(element: QuadSolid2D, target_t_id: int) -> PolygonSolid2D:
    return _copy_with_payload(element, target_t_id, element.corner_node_ids)


def _polygon_to_quad(element: PolygonSolid2D, target_t_id: int) -> QuadSolid2D:
    if len(element.node_ids) != 4:
        raise ValueError(
            f"单元 {element.e_id} 为 {len(element.node_ids)} 节点多边形，"
            "不能唯一转为四节点二维单元"
        )
    return _copy_with_payload(element, target_t_id, element.node_ids)


def _quadratic_2d_to_edge_structured(
    element: QuadraticQuad2D | QuadraticTriangle2D,
    target_t_id: int,
) -> EdgeStructured2D:
    corners = element.corner_node_ids
    mids = element.edge_node_ids
    if target_t_id in {444, 644}:
        edge_orders = tuple(_QUADRATIC_ORDER for _ in corners)
        return EdgeStructured2D(
            element.e_id,
            target_t_id,
            element.c_id,
            element.m_id,
            element.d_id,
            element.f_id,
            (*corners, *mids),
            tuple(order + 1 for order in edge_orders),
            edge_orders,
        )
    edges = tuple(
        (corners[index], mids[index], corners[(index + 1) % len(corners)])
        for index in range(len(corners))
    )
    return EdgeStructured2D.from_edges(
        element.e_id,
        target_t_id,
        element.c_id,
        element.m_id,
        element.d_id,
        element.f_id,
        edges,
    )


def _edge_structured_to_quadratic_2d(
    element: EdgeStructured2D,
    target_t_id: int,
) -> QuadraticQuad2D | QuadraticTriangle2D:
    edges = element.edges()
    if len(edges) not in {3, 4} or any(len(edge) != 3 for edge in edges):
        raise ValueError(
            f"单元 {element.e_id} 的边结构不是三边/四边二阶形式，"
            "不能唯一转为常规二维二阶单元"
        )
    corners = tuple(edge[0] for edge in edges)
    mids = tuple(edge[1] for edge in edges)
    return _copy_with_payload(element, target_t_id, (*corners, *mids))


def _hex_to_polyhedron(element: Hexahedron, target_t_id: int) -> Polyhedron:
    return Polyhedron.from_faces(
        element.e_id,
        target_t_id,
        element.c_id,
        element.m_id,
        element.d_id,
        element.f_id,
        element.faces(),
    )


def _polyhedron_to_hex(element: Polyhedron, target_t_id: int) -> Hexahedron:
    faces = element.faces()
    face_sets = {frozenset(face) for face in faces}
    unique = tuple(dict.fromkeys(node_id for face in faces for node_id in face))
    if len(unique) != 8 or len(faces) != 6 or any(len(face) != 4 for face in faces):
        raise ValueError(
            f"单元 {element.e_id} 不是可唯一识别的八节点六面体多面体"
        )
    for bottom in faces:
        bottom_set = set(bottom)
        for top in faces:
            if top is bottom or bottom_set & set(top):
                continue
            candidate_ids = tuple(reversed(bottom)) + tuple(top)
            candidate_face_sets = {
                frozenset(face) for face in Hexahedron(
                    element.e_id,
                    target_t_id,
                    element.c_id,
                    element.m_id,
                    element.d_id,
                    element.f_id,
                    candidate_ids,
                ).faces()
            }
            if candidate_face_sets == face_sets:
                return _copy_with_payload(element, target_t_id, candidate_ids)
    raise ValueError(
        f"单元 {element.e_id} 的面拓扑不能按当前规则唯一还原为 Hexahedron"
    )


def _higher_order_faces_from_regular(element: BaseElement) -> tuple[int, tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]]:
    if isinstance(element, HigherOrderHexahedron):
        return (
            6,
            tuple(tuple(_QUADRATIC_ORDER for _ in range(4)) for _ in range(6)),
            tuple(tuple(face) for face in _hex20_faces(element.node_ids)),
        )
    if isinstance(element, (HigherOrderWedge, HigherOrderWedgeAlt)):
        face_nodes = _wedge15_faces(
            element.node_ids, isinstance(element, HigherOrderWedgeAlt)
        )
        return (
            5,
            tuple(
                tuple(_QUADRATIC_ORDER for _ in range(edge_count))
                for edge_count in (4, 4, 4, 3, 3)
            ),
            tuple(tuple(face) for face in face_nodes),
        )
    raise ValueError(f"单元 {element.e_id} 不是已支持的常规三维高阶单元")


def _regular_high_order_to_higher_order(
    element: BaseElement,
    target_t_id: int,
) -> HigherOrder:
    _, edge_orders, face_nodes = _higher_order_faces_from_regular(element)
    return HigherOrder.from_structure(
        element.e_id,
        target_t_id,
        element.c_id,
        element.m_id,
        element.d_id,
        element.f_id,
        edge_orders,
        face_nodes,
    )


def _higher_order_to_regular(element: HigherOrder, target_t_id: int) -> BaseElement:
    if not all(
        order == _QUADRATIC_ORDER
        for orders in element.face_edge_orders
        for order in orders
    ):
        raise ValueError(f"单元 {element.e_id} 不是统一二阶 HigherOrder，不能反转")

    faces = element.face_nodes
    if target_t_id in HigherOrderHexahedron.COMPATIBLE_TYPES:
        if len(faces) != 6 or any(len(face) != 8 for face in faces):
            raise ValueError(f"单元 {element.e_id} 不是 20 节点六面体面结构")
        f0, f1, f2, f3, f4, _f5 = faces
        payload = (
            f0[0], f0[1], f1[3], f1[0],
            f0[3], f0[2], f1[2], f1[1],
            f0[4], _f5[4], f2[5], f2[4],
            f0[7], f0[5], f1[6], f1[4],
            f0[6], f4[5], f1[5], f3[5],
        )
        candidate = _copy_with_payload(element, target_t_id, payload)
    elif target_t_id in (
        HigherOrderWedge.COMPATIBLE_TYPES | HigherOrderWedgeAlt.COMPATIBLE_TYPES
    ):
        if len(faces) != 5 or any(
            len(face) != expected for face, expected in zip(faces, (8, 8, 8, 6, 6))
        ):
            raise ValueError(f"单元 {element.e_id} 不是 15 节点三棱柱面结构")
        f0, f1, f2, _f3, f4 = faces
        base = (
            f0[0], f0[1], f1[1],
            f0[3], f0[2], f1[2],
            f0[4], f1[4], f2[4],
        )
        vertical = (f0[7], f0[5], f1[5])
        top = (f0[6], f4[4], f4[5])
        if target_t_id in HigherOrderWedge.COMPATIBLE_TYPES:
            payload = (*base, *vertical, *top)
        else:
            payload = (*base, *top, *vertical)
        candidate = _copy_with_payload(element, target_t_id, payload)
    else:
        raise ValueError(f"目标类型 {target_t_id} 不是常规三维高阶单元")

    _, expected_orders, expected_faces = _higher_order_faces_from_regular(candidate)
    if expected_orders != element.face_edge_orders or expected_faces != element.face_nodes:
        raise ValueError(
            f"单元 {element.e_id} 的 HigherOrder 面结构不能唯一还原为 {target_t_id}"
        )
    return candidate


_AUTO_REGULAR_HIGH_ORDER_TARGET = 0
_REGULAR_HIGH_ORDER_TARGETS_BY_HIGHER_ORDER: dict[int, tuple[int, ...]] = {
    508: (16, 18, 20),
    805: (510, 170, 190),
    807: (511, 171, 191),
}


def _higher_order_structure_summary(element: HigherOrder) -> str:
    face_parts = []
    for index, (edge_count, orders, nodes) in enumerate(
        zip(element.face_edge_counts, element.face_edge_orders, element.face_nodes),
        1,
    ):
        face_parts.append(
            f"第{index}面：{edge_count}边，阶次{tuple(orders)}，节点数{len(nodes)}"
        )
    return (
        f"n_faces={element.n_faces}；"
        f"face_edge_counts={element.face_edge_counts}；"
        + "；".join(face_parts)
    )


def _auto_higher_order_to_regular(element: HigherOrder) -> BaseElement:
    target_t_ids = _REGULAR_HIGH_ORDER_TARGETS_BY_HIGHER_ORDER.get(element.t_id)
    if target_t_ids is None:
        raise ValueError(
            f"单元 {element.e_id} 的任意高阶类型 {element.t_id} "
            "没有配置自动转常规高阶候选"
        )
    errors: list[str] = []
    for target_t_id in target_t_ids:
        try:
            return _higher_order_to_regular(element, target_t_id)
        except ValueError as exc:
            errors.append(f"{target_t_id}: {exc}")
    raise ValueError(
        f"单元 {element.e_id} 的任意高阶结构为："
        f"{_higher_order_structure_summary(element)}；"
        "无对应的常规单元。"
    )


def _auto_edge_structured_to_quadratic(element: EdgeStructured2D) -> BaseElement:
    """EdgeStructured2D 自动转为边数匹配且响应类型相同的常规二维二阶单元。

    3 条边 → QuadraticTriangle2D，4 条边 → QuadraticQuad2D；
    目标 t_id 选择与源单元响应类型（单相/直接求解/交叉迭代）一致的类型号。
    """
    edges = element.edges()
    edge_count = len(edges)
    if edge_count == 3:
        target_class = QuadraticTriangle2D
    elif edge_count == 4:
        target_class = QuadraticQuad2D
    else:
        raise ValueError(
            f"EdgeStructured2D 单元 {element.e_id} 有 {edge_count} 条边，"
            "仅支持 3 边（三角形）或 4 边（四边形）自动转换"
        )
    if any(len(edge) != 3 for edge in edges):
        raise ValueError(
            f"EdgeStructured2D 单元 {element.e_id} 的边不是统一二阶，"
            "无法自动转为常规二维二阶单元"
        )

    source_response = element_response_type(element.t_id)
    candidates = [
        t_id
        for t_id in sorted(target_class.COMPATIBLE_TYPES)
        if element_response_type(t_id) == source_response
    ]
    if not candidates:
        raise ValueError(
            f"EdgeStructured2D 单元 {element.e_id}（{source_response.label}）"
            f"在 {target_class.__name__} 中无对应响应类型的 t_id"
        )
    target_t_id = candidates[0]
    return _edge_structured_to_quadratic_2d(element, target_t_id)


def convert_element_topology(element: BaseElement, target_t_id: int) -> BaseElement:
    """按已知安全规则执行单个单元拓扑互转。"""
    target_t_id = int(target_t_id)
    if target_t_id == _AUTO_REGULAR_HIGH_ORDER_TARGET:
        if isinstance(element, HigherOrder):
            return _auto_higher_order_to_regular(element)
        if isinstance(element, EdgeStructured2D):
            return _auto_edge_structured_to_quadratic(element)
        raise ValueError(
            "目标类型 0（自动）当前仅支持：\n"
            "  - HigherOrder(508/805/807) → 常规高阶(16/18/20/…)\n"
            "  - EdgeStructured2D(443/444/644) → 常规二维二阶(11/102/104/…)"
        )
    if target_t_id == element.t_id:
        return element
    try:
        return replace_element_type(element, target_t_id)
    except ValueError as same_structure_error:
        if target_t_id in PolygonSolid2D.COMPATIBLE_TYPES and isinstance(element, QuadSolid2D):
            return _quad_to_polygon(element, target_t_id)
        if target_t_id in QuadSolid2D.COMPATIBLE_TYPES and isinstance(element, PolygonSolid2D):
            return _polygon_to_quad(element, target_t_id)
        if target_t_id in EdgeStructured2D.COMPATIBLE_TYPES and isinstance(
            element, (QuadraticQuad2D, QuadraticTriangle2D)
        ):
            return _quadratic_2d_to_edge_structured(element, target_t_id)
        if target_t_id in (
            QuadraticQuad2D.COMPATIBLE_TYPES | QuadraticTriangle2D.COMPATIBLE_TYPES
        ) and isinstance(element, EdgeStructured2D):
            return _edge_structured_to_quadratic_2d(element, target_t_id)
        if target_t_id in Polyhedron.COMPATIBLE_TYPES and isinstance(element, Hexahedron):
            return _hex_to_polyhedron(element, target_t_id)
        if target_t_id in Hexahedron.COMPATIBLE_TYPES and isinstance(element, Polyhedron):
            return _polyhedron_to_hex(element, target_t_id)
        if target_t_id in HigherOrder.COMPATIBLE_TYPES and isinstance(
            element, (HigherOrderHexahedron, HigherOrderWedge, HigherOrderWedgeAlt)
        ):
            return _regular_high_order_to_higher_order(element, target_t_id)
        if isinstance(element, HigherOrder) and target_t_id in (
            HigherOrderHexahedron.COMPATIBLE_TYPES
            | HigherOrderWedge.COMPATIBLE_TYPES
            | HigherOrderWedgeAlt.COMPATIBLE_TYPES
        ):
            return _higher_order_to_regular(element, target_t_id)
        raise same_structure_error


def convert_element_types_by_material(
    input_path: str, control_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    """按材料号和类型映射执行安全单元互转。

    控制文件格式与“按材料修改单元类型”一致：
    材料数量；逐行材料号；转换对数量；逐行“旧类型 新类型”。
    """
    materials, type_mapping = _parse_material_type_conversion_control(control_path)

    def mutate(mesh: Mesh) -> int:
        changed = 0
        for index, element in enumerate(mesh.elements):
            new_type = type_mapping.get(element.t_id)
            if element.m_id not in materials or new_type is None:
                continue
            mesh.elements[index] = convert_element_topology(element, new_type)
            changed += 1
        return changed

    return _write_modified(
        input_path,
        output_path,
        mutate,
        overwrite=overwrite,
        title="按材料单元互转",
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


def _read_center_node_scale_control(path: str | Path) -> tuple[int, tuple[float, float, float]]:
    values: dict[str, str] = {}
    for line in clean_control_lines(path):
        if "=" not in line:
            raise ValueError(f"中心节点缩放控制行缺少 '='：{line}")
        key, value = line.split("=", 1)
        values[key.strip().upper()] = value.strip()
    if "CENTER_NODE_ID" not in values:
        raise ValueError("中心节点缩放控制文件缺少参数：CENTER_NODE_ID")

    center_node_id = int(values["CENTER_NODE_ID"])
    uniform_factor = float(values.get("SCALE_FACTOR", "1.0"))
    scale_factors = (
        float(values.get("SCALE_X", uniform_factor)),
        float(values.get("SCALE_Y", uniform_factor)),
        float(values.get("SCALE_Z", uniform_factor)),
    )
    if any(not math.isfinite(factor) or factor <= 0 for factor in scale_factors):
        raise ValueError("缩放系数必须为有限正数")
    return center_node_id, scale_factors


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


def scale_all_nodes_by_center_node(
    input_path: str, control_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    center_node_id, scale_factors = _read_center_node_scale_control(control_path)
    source, target = checked_paths(input_path, output_path)
    mesh = read_mesh(source)
    if center_node_id not in mesh.node_map:
        raise ValueError(f"中心节点 {center_node_id} 不存在")

    center_node = mesh.node_map[center_node_id]
    center = center_node.coordinates
    changed = 0
    for node in mesh.nodes:
        old_coordinates = node.coordinates
        node.x = center[0] + (node.x - center[0]) * scale_factors[0]
        node.y = center[1] + (node.y - center[1]) * scale_factors[1]
        node.z = center[2] + (node.z - center[2]) * scale_factors[2]
        if node.coordinates != old_coordinates:
            changed += 1
    mesh.invalidate_geometry_cache()
    write_mesh(target, mesh, overwrite=overwrite)
    return OperationResult(
        "以节点为中心缩放所有节点",
        f"处理完成：以节点 {center_node_id} 为中心缩放 {len(mesh.nodes)} 个节点，"
        f"其中 {changed} 个节点坐标发生变化。",
        (target,),
        {
            "nodes": len(mesh.nodes),
            "elements": len(mesh.elements),
            "changed": changed,
            "center_node_id": center_node_id,
            "scale_x": scale_factors[0],
            "scale_y": scale_factors[1],
            "scale_z": scale_factors[2],
        },
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
    """按材料输出单元网格，将指定材料的单元合并到一个文件中。

    Export element mesh by material — combine elements of all specified
    materials into a single output file with their referenced nodes.
    """
    source, target = checked_paths(input_path, output_path)
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

    selected_elements: list[BaseElement] = []
    per_material_counts: dict[str, int] = {}
    for m_id in material_ids:
        elements = material_elements[m_id]
        selected_elements.extend(elements)
        per_material_counts[str(m_id)] = len(elements)

    referenced: set[int] = set()
    for element in selected_elements:
        referenced.update(element.node_ids)
    selected_nodes = [
        node for node in mesh.nodes if node.node_id in referenced
    ]

    write_mesh(
        target,
        mesh,
        nodes=selected_nodes,
        elements=selected_elements,
        overwrite=overwrite,
    )

    return OperationResult(
        "按材料输出单元网格",
        f"已完成 {len(material_ids)} 种材料的单元导出，"
        f"共输出 {len(selected_elements)} 个单元、{len(selected_nodes)} 个引用节点。",
        (target,),
        {
            "material_count": len(material_ids),
            "total_elements": len(selected_elements),
            "total_nodes": len(selected_nodes),
            **per_material_counts,
        },
    )


def delete_elements_by_material(
    input_path: str,
    control_path: str,
    output_path: str,
    *,
    overwrite: bool = False,
) -> OperationResult:
    """删除指定材料的单元，保留其余单元和引用节点。

    Delete elements of specified materials, keeping the rest.
    """
    source, target = checked_paths(input_path, output_path)
    material_ids = _parse_material_list(control_path)
    delete_set = set(material_ids)
    mesh = read_mesh(source)

    missing = [m_id for m_id in material_ids if not any(e.m_id == m_id for e in mesh.elements)]
    if missing:
        raise ValueError(
            f"以下材料号在网格中不存在：{', '.join(str(m) for m in missing)}"
        )

    kept_elements = [e for e in mesh.elements if e.m_id not in delete_set]
    if not kept_elements:
        raise ValueError("删除后网格中无剩余单元，请检查材料列表")

    referenced: set[int] = set()
    for element in kept_elements:
        referenced.update(element.node_ids)
    kept_nodes = [node for node in mesh.nodes if node.node_id in referenced]

    write_mesh(
        target,
        mesh,
        nodes=kept_nodes,
        elements=kept_elements,
        overwrite=overwrite,
    )

    deleted_count = len(mesh.elements) - len(kept_elements)
    return OperationResult(
        "按材料删除单元",
        f"已删除 {deleted_count} 个单元（材料 {', '.join(str(m) for m in material_ids)}），"
        f"保留 {len(kept_elements)} 个单元、{len(kept_nodes)} 个节点。",
        (target,),
        {
            "deleted_elements": deleted_count,
            "kept_elements": len(kept_elements),
            "kept_nodes": len(kept_nodes),
        },
    )


# ---------------------------------------------------------------------------
# 常规高阶 → 任意高阶（面结构化 HigherOrder）转换
# ---------------------------------------------------------------------------

_TARGET_MAP: dict[int, int] = {
    16: 508, 18: 508, 20: 508,
    510: 805, 170: 805, 190: 805,
    511: 807, 171: 807, 191: 807,
}
_QUADRATIC_ORDER = 2  # 二阶边：起点 + 中点；终点由下一条边的起点表示


def _hex20_faces(ids: tuple[int, ...]) -> list[list[int]]:
    """20 节点六面体转换为“4角点 + 4边内部节点”的 6 个面。"""
    b0, b1, b2, b3 = ids[0], ids[1], ids[2], ids[3]
    t0, t1, t2, t3 = ids[4], ids[5], ids[6], ids[7]
    bm0, bm1, bm2, bm3 = ids[8], ids[9], ids[10], ids[11]
    vm0, vm1, vm2, vm3 = ids[12], ids[13], ids[14], ids[15]
    tm0, tm1, tm2, tm3 = ids[16], ids[17], ids[18], ids[19]

    return [
        # 左侧面：角点 1,2,6,5；边内部节点 9,14,17,13
        [b0, b1, t1, t0, bm0, vm1, tm0, vm0],
        # 右侧面：角点 4,8,7,3；边内部节点 16,19,15,11
        [b3, t3, t2, b2, vm3, tm2, vm2, bm2],
        # 底面：角点 1,4,3,2；边内部节点 12,11,10,9
        [b0, b3, b2, b1, bm3, bm2, bm1, bm0],
        # 前侧面：角点 1,5,8,4；边内部节点 13,20,16,12
        [b0, t0, t3, b3, vm0, tm3, vm3, bm3],
        # 顶面：角点 5,6,7,8；边内部节点 17,18,19,20
        [t0, t1, t2, t3, tm0, tm1, tm2, tm3],
        # 后侧面：角点 2,3,7,6；边内部节点 10,15,18,14
        [b1, b2, t2, t1, bm1, vm2, tm1, vm1],
    ]


def _wedge15_faces(ids: tuple[int, ...], is_alt: bool) -> list[list[int]]:
    """15 节点三棱柱的 5 个面（2 三角 + 3 四边）。

    is_alt=False: HigherOrderWedge (18/170/171)
      mid-edge order: bottom(7-9), vertical(10-12), top(13-15)
    is_alt=True:  HigherOrderWedgeAlt (20/190/191)
      mid-edge order: bottom(7-9), top(10-12), vertical(13-15)
    """
    b0, b1, b2 = ids[0], ids[1], ids[2]
    t0, t1, t2 = ids[3], ids[4], ids[5]
    bm0, bm1, bm2 = ids[6], ids[7], ids[8]
    if is_alt:
        tm0, tm1, tm2 = ids[9], ids[10], ids[11]
        vm0, vm1, vm2 = ids[12], ids[13], ids[14]
    else:
        vm0, vm1, vm2 = ids[9], ids[10], ids[11]
        tm0, tm1, tm2 = ids[12], ids[13], ids[14]

    return [
        # 侧面四边形 1 (1→2→5→4)
        [b0, b1, t1, t0, bm0, vm1, tm0, vm0],
        # 侧面四边形 2 (2→3→6→5)
        [b1, b2, t2, t1, bm1, vm2, tm1, vm1],
        # 侧面四边形 3 (3→1→4→6)
        [b2, b0, t0, t2, bm2, vm0, tm2, vm2],
        # 底面三角：角点 1→3→2，随后为对应三边内部节点
        [b0, b2, b1, bm2, bm1, bm0],
        # 顶面三角 (4→5→6)
        [t0, t1, t2, tm0, tm1, tm2],
    ]


def convert_to_higher_order(
    input_path: str,
    output_path: str,
    *,
    overwrite: bool = False,
) -> OperationResult:
    """将常规高阶单元转换为面结构化任意高阶单元。

    映射关系：
      16, 18, 20        → 508
      510, 170, 190     → 805
      511, 171, 191     → 807

    二阶边的 Payload E 表达为 ``order=2``。每个面先写全部角点，再按面内
    边顺序写每条边的一个中点。

    20 节点六面体 → 6 个四边形面，每面 4 边 × 2 阶 = 8 节点
    15 节点三棱柱 → 3 个四边形面（8节点）+ 2 个三角面（6节点）
    """
    source, target = checked_paths(input_path, output_path)
    mesh = read_mesh(source)
    changed = 0

    for index, element in enumerate(mesh.elements):
        target_t_id = _TARGET_MAP.get(element.t_id)
        if target_t_id is None:
            continue

        ids = element.node_ids

        if isinstance(element, HigherOrderHexahedron):
            face_nodes = _hex20_faces(ids)
            edges_per_face = (4, 4, 4, 4, 4, 4)
        elif isinstance(element, (HigherOrderWedge, HigherOrderWedgeAlt)):
            is_alt = isinstance(element, HigherOrderWedgeAlt)
            face_nodes = _wedge15_faces(ids, is_alt)
            edges_per_face = (4, 4, 4, 3, 3)
        else:
            continue

        edge_orders: tuple[tuple[int, ...], ...] = tuple(
            tuple(_QUADRATIC_ORDER for _ in range(edge_count))
            for edge_count in edges_per_face
        )
        mesh.elements[index] = HigherOrder.from_structure(
            element.e_id,
            target_t_id,
            element.c_id,
            element.m_id,
            element.d_id,
            element.f_id,
            edge_orders,
            tuple(tuple(f) for f in face_nodes),
        )
        changed += 1

    if changed == 0:
        raise ValueError("网格中没有可转换的常规高阶单元（16/18/20/170/171/190/191/510/511）")

    write_mesh(target, mesh, overwrite=overwrite)
    return OperationResult(
        "常规高阶转任意高阶",
        f"转换完成：共转换 {changed} 个单元。",
        (target,),
        {"converted": changed, "total_elements": len(mesh.elements)},
    )
