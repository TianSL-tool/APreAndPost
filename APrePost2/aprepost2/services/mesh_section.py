from __future__ import annotations

from itertools import product
from pathlib import Path
import re

import numpy as np

from aprepost2.domain import (
    ElementResponseType,
    Mesh,
    Node,
    create_element,
    element_response_type,
)
from aprepost2.io.mesh_io import read_mesh, write_mesh
from aprepost2.services.common import OperationResult, checked_paths


def _parse_material_ids(value: str) -> frozenset[int] | None:
    text = str(value).strip().lower()
    if text in {"all", "全部", "*", "0"}:
        return None
    tokens = [token for token in re.split(r"[,;\s]+", text) if token]
    if not tokens:
        raise ValueError("材料号不能为空；提取全部材料时填写 all")
    try:
        return frozenset(int(token) for token in tokens)
    except ValueError as exc:
        raise ValueError("材料号应为用空格、逗号或分号分隔的整数") from exc


class _SectionNodeRegistry:
    """按空间容差复用截面节点，并优先保留原网格平面节点编号。"""

    def __init__(self, mesh: Mesh, tolerance: float) -> None:
        self.tolerance = float(tolerance)
        self.next_node_id = max(mesh.node_map) + 1
        self.nodes: dict[int, Node] = {}
        self._buckets: dict[tuple[int, int, int], list[int]] = {}
        self._edge_intersections: dict[tuple[int, int], int] = {}
        self._mesh = mesh

    def _key(self, coordinates: np.ndarray) -> tuple[int, int, int]:
        return tuple(np.floor(coordinates / self.tolerance).astype(np.int64))

    def _remember(self, node: Node, *, index_spatially: bool = True) -> int:
        if node.node_id not in self.nodes:
            self.nodes[node.node_id] = node
            coordinates = np.asarray(node.coordinates, dtype=np.float64)
            if index_spatially:
                self._buckets.setdefault(self._key(coordinates), []).append(node.node_id)
        return node.node_id

    def existing(self, node_id: int) -> int:
        return self._remember(
            self._mesh.node_map[int(node_id)], index_spatially=False
        )

    def intersection(self, coordinates: np.ndarray) -> int:
        key = self._key(coordinates)
        for offset in product((-1, 0, 1), repeat=3):
            neighbor = tuple(key[index] + offset[index] for index in range(3))
            for node_id in self._buckets.get(neighbor, ()):
                node = self.nodes[node_id]
                if np.linalg.norm(
                    np.asarray(node.coordinates, dtype=np.float64) - coordinates
                ) <= self.tolerance:
                    return node_id
        node_id = self.next_node_id
        self.next_node_id += 1
        return self._remember(Node(node_id, *map(float, coordinates)))


    def intersection_on_edge(
        self,
        first_id: int,
        second_id: int,
        coordinates: np.ndarray,
        *,
        merge_by_coordinates: bool,
    ) -> int:
        edge = tuple(sorted((int(first_id), int(second_id))))
        existing_id = self._edge_intersections.get(edge)
        if existing_id is not None:
            return existing_id
        if merge_by_coordinates:
            node_id = self.intersection(coordinates)
        else:
            node_id = self.next_node_id
            self.next_node_id += 1
            self.nodes[node_id] = Node(node_id, *map(float, coordinates))
        self._edge_intersections[edge] = node_id
        return node_id

def _ordered_section_polygon(
    element,
    mesh: Mesh,
    registry: _SectionNodeRegistry,
    origin: np.ndarray,
    normal: np.ndarray,
    tolerance: float,
) -> tuple[int, ...]:
    intersection_ids: set[int] = set()
    visited_edges: set[tuple[int, int]] = set()

    for face in element.faces():
        if len(face) < 2:
            continue
        for index, first_id in enumerate(face):
            second_id = face[(index + 1) % len(face)]
            edge = tuple(sorted((int(first_id), int(second_id))))
            if edge in visited_edges or edge[0] == edge[1]:
                continue
            visited_edges.add(edge)
            first = np.asarray(mesh.node_map[first_id].coordinates, dtype=np.float64)
            second = np.asarray(mesh.node_map[second_id].coordinates, dtype=np.float64)
            first_distance = float(np.dot(first - origin, normal))
            second_distance = float(np.dot(second - origin, normal))
            first_on = abs(first_distance) <= tolerance
            second_on = abs(second_distance) <= tolerance

            if first_on:
                intersection_ids.add(registry.existing(first_id))
            if second_on:
                intersection_ids.add(registry.existing(second_id))
            if (
                not first_on
                and not second_on
                and first_distance * second_distance < 0.0
            ):
                ratio = first_distance / (first_distance - second_distance)
                coordinates = first + ratio * (second - first)
                intersection_ids.add(
                    registry.intersection_on_edge(
                        first_id,
                        second_id,
                        coordinates,
                        merge_by_coordinates=True,
                    )
                )

    if len(intersection_ids) < 3:
        return ()

    ids = list(intersection_ids)
    points = np.asarray(
        [registry.nodes[node_id].coordinates for node_id in ids], dtype=np.float64
    )
    center = np.mean(points, axis=0)
    reference = np.zeros(3)
    reference[int(np.argmin(np.abs(normal)))] = 1.0
    axis_u = np.cross(reference, normal)
    axis_u /= np.linalg.norm(axis_u)
    axis_v = np.cross(normal, axis_u)
    offsets = points - center
    angles = np.arctan2(offsets @ axis_v, offsets @ axis_u)
    ordered = tuple(ids[index] for index in np.argsort(angles))

    ordered_points = np.asarray(
        [registry.nodes[node_id].coordinates for node_id in ordered],
        dtype=np.float64,
    )
    area_vector = np.zeros(3)
    for index, point in enumerate(ordered_points):
        area_vector += np.cross(point, ordered_points[(index + 1) % len(ordered_points)])
    if 0.5 * np.linalg.norm(area_vector) <= tolerance * tolerance:
        return ()
    if float(np.dot(area_vector, normal)) < 0.0:
        ordered = tuple(reversed(ordered))
    return ordered



CONTACT_3D_TO_2D = {9: 4, 902: 700, 903: 777}
SOLID_POLYGON_TYPE = {
    ElementResponseType.SINGLE_PHASE: 44,
    ElementResponseType.SATURATED_POROUS_DIRECT: 47,
    ElementResponseType.SATURATED_POROUS_STAGGERED: 470,
}
SOLID_QUAD_TYPE = {
    ElementResponseType.SINGLE_PHASE: 1,
    ElementResponseType.SATURATED_POROUS_DIRECT: 2,
    ElementResponseType.SATURATED_POROUS_STAGGERED: 222,
}


def _solid_section_type(source_t_id: int, node_count: int) -> int:
    try:
        response_type = element_response_type(source_t_id)
    except ValueError:
        response_type = ElementResponseType.SINGLE_PHASE
    if node_count in {3, 4}:
        return SOLID_QUAD_TYPE[response_type]
    return SOLID_POLYGON_TYPE[response_type]


def _solid_section_payload(polygon: tuple[int, ...]) -> tuple[int, ...]:
    if len(polygon) == 3:
        return (*polygon, polygon[-1])
    return polygon




def _surface_section_segment(
    surface: tuple[int, ...],
    mesh: Mesh,
    registry: _SectionNodeRegistry,
    origin: np.ndarray,
    normal: np.ndarray,
    tolerance: float,
) -> tuple[int, int] | None:
    intersection_ids: set[int] = set()
    for index, first_id in enumerate(surface):
        second_id = surface[(index + 1) % len(surface)]
        if first_id == second_id:
            continue
        first = np.asarray(mesh.node_map[first_id].coordinates, dtype=np.float64)
        second = np.asarray(mesh.node_map[second_id].coordinates, dtype=np.float64)
        first_distance = float(np.dot(first - origin, normal))
        second_distance = float(np.dot(second - origin, normal))
        first_on = abs(first_distance) <= tolerance
        second_on = abs(second_distance) <= tolerance
        if first_on:
            intersection_ids.add(registry.existing(first_id))
        if second_on:
            intersection_ids.add(registry.existing(second_id))
        if (
            not first_on
            and not second_on
            and first_distance * second_distance < 0.0
        ):
            ratio = first_distance / (first_distance - second_distance)
            coordinates = first + ratio * (second - first)
            intersection_ids.add(
                registry.intersection_on_edge(
                    first_id,
                    second_id,
                    coordinates,
                    merge_by_coordinates=False,
                )
            )
    if len(intersection_ids) != 2:
        return None
    first_id, second_id = intersection_ids
    return int(first_id), int(second_id)


def _ordered_contact_section(
    element,
    mesh: Mesh,
    registry: _SectionNodeRegistry,
    origin: np.ndarray,
    normal: np.ndarray,
    tolerance: float,
) -> tuple[int, int, int, int] | None:
    node_ids = element.structured_node_ids()
    bottom = _surface_section_segment(
        tuple(node_ids[:4]), mesh, registry, origin, normal, tolerance
    )
    top = _surface_section_segment(
        tuple(node_ids[4:]), mesh, registry, origin, normal, tolerance
    )
    if bottom is None or top is None:
        return None
    bottom_points = np.asarray(
        [registry.nodes[node_id].coordinates for node_id in bottom], dtype=np.float64
    )
    direction = bottom_points[1] - bottom_points[0]
    direction_norm = float(np.linalg.norm(direction))
    if direction_norm <= tolerance:
        return None
    direction /= direction_norm
    dominant = int(np.argmax(np.abs(direction)))
    if direction[dominant] < 0.0:
        direction = -direction

    def ordered(segment: tuple[int, int]) -> tuple[int, int]:
        return tuple(
            sorted(
                segment,
                key=lambda node_id: float(
                    np.dot(np.asarray(registry.nodes[node_id].coordinates), direction)
                ),
            )
        )

    bottom_ordered = ordered(bottom)
    top_ordered = tuple(reversed(ordered(top)))
    return (*bottom_ordered, *top_ordered)




def _ordered_contact_mid_section(
    element,
    mesh: Mesh,
    registry: _SectionNodeRegistry,
    origin: np.ndarray,
    normal: np.ndarray,
    tolerance: float,
) -> tuple[int, int, int, int] | None:
    node_ids = element.structured_node_ids()
    bottom_ids = tuple(node_ids[:4])
    top_ids = tuple(node_ids[4:])
    bottom_points = np.asarray(
        [mesh.node_map[node_id].coordinates for node_id in bottom_ids], dtype=float
    )
    top_points = np.asarray(
        [mesh.node_map[node_id].coordinates for node_id in top_ids], dtype=float
    )
    middle_points = 0.5 * (bottom_points + top_points)
    distances = (middle_points - origin) @ normal
    locations: dict[tuple[str, int], tuple[int, float]] = {}
    for index in range(4):
        next_index = (index + 1) % 4
        first_distance = float(distances[index])
        second_distance = float(distances[next_index])
        first_on = abs(first_distance) <= tolerance
        second_on = abs(second_distance) <= tolerance
        if first_on:
            locations[("vertex", index)] = (index, 0.0)
        if second_on:
            locations[("vertex", next_index)] = (next_index, 0.0)
        if not first_on and not second_on and first_distance * second_distance < 0.0:
            ratio = first_distance / (first_distance - second_distance)
            locations[("edge", index)] = (index, float(ratio))
    if len(locations) != 2:
        return None

    paired_nodes: list[tuple[int, int]] = []
    for (kind, _), (index, ratio) in locations.items():
        if kind == "vertex":
            paired_nodes.append(
                (registry.existing(bottom_ids[index]), registry.existing(top_ids[index]))
            )
            continue
        next_index = (index + 1) % 4
        bottom_point = bottom_points[index] + ratio * (
            bottom_points[next_index] - bottom_points[index]
        )
        top_point = top_points[index] + ratio * (
            top_points[next_index] - top_points[index]
        )
        paired_nodes.append(
            (
                registry.intersection_on_edge(
                    bottom_ids[index], bottom_ids[next_index], bottom_point,
                    merge_by_coordinates=False,
                ),
                registry.intersection_on_edge(
                    top_ids[index], top_ids[next_index], top_point,
                    merge_by_coordinates=False,
                ),
            )
        )

    first_point = np.asarray(registry.nodes[paired_nodes[0][0]].coordinates)
    second_point = np.asarray(registry.nodes[paired_nodes[1][0]].coordinates)
    direction = second_point - first_point
    if np.linalg.norm(direction) <= tolerance:
        return None
    dominant = int(np.argmax(np.abs(direction)))
    if direction[dominant] < 0.0:
        paired_nodes.reverse()
    bottom_ordered = (paired_nodes[0][0], paired_nodes[1][0])
    top_reversed = (paired_nodes[1][1], paired_nodes[0][1])
    return (*bottom_ordered, *top_reversed)


def extract_mesh_section(
    input_path: str,
    output_path: str,
    origin_x: float,
    origin_y: float,
    origin_z: float,
    normal_x: float,
    normal_y: float,
    normal_z: float,
    material_ids: str = "all",
    tolerance: float = 1.0e-6,
    *,
    overwrite: bool = False,
) -> OperationResult:
    """提取三维实体网格与给定平面的二维多边形截面。"""

    source, target = checked_paths(input_path, output_path)
    tolerance = float(tolerance)
    if not np.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("容差必须是有限正数")
    origin = np.asarray((origin_x, origin_y, origin_z), dtype=np.float64)
    normal = np.asarray((normal_x, normal_y, normal_z), dtype=np.float64)
    if not np.all(np.isfinite(origin)) or not np.all(np.isfinite(normal)):
        raise ValueError("截面原点和法向量必须是有限数值")
    normal_norm = float(np.linalg.norm(normal))
    if normal_norm <= tolerance:
        raise ValueError("截面法向量长度必须大于容差")
    normal /= normal_norm
    selected_materials = _parse_material_ids(material_ids)

    mesh = read_mesh(source)
    registry = _SectionNodeRegistry(mesh, tolerance)
    section_elements = []
    polygon_keys: set[tuple[int, ...]] = set()
    examined_count = 0
    contact_count = 0
    duplicate_count = 0
    unsupported_count = 0
    quad_count = 0

    triangle_count = 0
    for element in sorted(mesh.elements, key=lambda item: item.e_id):
        if selected_materials is not None and element.m_id not in selected_materials:
            continue

        target_contact_type = CONTACT_3D_TO_2D.get(element.t_id)
        if target_contact_type is not None:
            examined_count += 1
            contact = _ordered_contact_mid_section(
                element, mesh, registry, origin, normal, tolerance
            )
            if contact is None:
                continue
            contact_key = tuple(sorted(contact))
            if contact_key in polygon_keys:
                duplicate_count += 1
                continue
            polygon_keys.add(contact_key)
            section_elements.append(
                create_element(
                    element.e_id,
                    target_contact_type,
                    element.c_id,
                    element.m_id,
                    element.d_id,
                    element.f_id,
                    contact,
                )
            )
            contact_count += 1
            continue

        if not element.is_3d_solid:
            continue
        if element.polynomial_order != 1:
            unsupported_count += 1
            continue
        if not element.faces():
            unsupported_count += 1
            continue
        examined_count += 1
        polygon = _ordered_section_polygon(
            element, mesh, registry, origin, normal, tolerance
        )
        if not polygon:
            continue
        polygon_key = tuple(sorted(polygon))
        if polygon_key in polygon_keys:
            duplicate_count += 1
            continue
        polygon_keys.add(polygon_key)
        section_elements.append(
            create_element(
                element.e_id,
                _solid_section_type(element.t_id, len(polygon)),
                element.c_id,
                element.m_id,
                element.d_id,
                element.f_id,
                _solid_section_payload(polygon),
            )
        )


        if len(polygon) == 4:
            quad_count += 1
        elif len(polygon) == 3:
            triangle_count += 1

    if not section_elements:
        raise ValueError("给定平面未与筛选后的三维实体或 9 系列接触面形成有效截面")

    referenced_ids = {
        node_id for element in section_elements for node_id in element.node_ids
    }
    section_nodes = [registry.nodes[node_id] for node_id in sorted(referenced_ids)]
    section_mesh = Mesh(section_nodes, section_elements)
    section_mesh.validate_connectivity()
    write_mesh(target, section_mesh, overwrite=overwrite)
    new_node_count = sum(node_id not in mesh.node_map for node_id in referenced_ids)
    log_lines = (
        f"读取网格：{len(mesh.nodes)} 个节点，{len(mesh.elements)} 个单元",
        f"检查 {examined_count} 个三维实体/接触单元，提取 {len(section_elements)} 个二维截面单元",
        f"其中二维接触单元 {contact_count} 个，二维实体多边形 {len(section_elements) - contact_count} 个",
        f"截面节点 {len(section_nodes)} 个，其中新生成 {new_node_count} 个",
        f"去除重合截面 {duplicate_count} 个，跳过无面拓扑单元 {unsupported_count} 个",
        f"截面法向量：({normal[0]:.8g}, {normal[1]:.8g}, {normal[2]:.8g})",
        f"自动转换四边形 {quad_count} 个、退化三角形 {triangle_count} 个",
    )
    return OperationResult(
        "三维网格截面抽取",
        f"截面抽取完成：生成 {len(section_elements)} 个二维截面单元，其中接触单元 {contact_count} 个。",
        (Path(target),),
        {
            "section_elements": len(section_elements),
            "section_nodes": len(section_nodes),
            "section_contacts": contact_count,
            "new_nodes": new_node_count,
            "duplicate_sections": duplicate_count,
            "section_quads": quad_count,
            "section_triangles": triangle_count,
        },
        log_lines,
    )
