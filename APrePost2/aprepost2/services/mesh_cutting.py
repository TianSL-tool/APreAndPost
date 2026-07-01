from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aprepost2.domain import BaseElement, Mesh, Node
from aprepost2.domain.element import (
    Polyhedron,
    PolygonContact,
    _deduplicate_polygon,
)
from aprepost2.io.mesh_io import read_mesh, write_mesh
from aprepost2.io.text import clean_control_lines
from aprepost2.services.common import OperationResult, checked_paths


@dataclass(frozen=True, slots=True)
class CuttingPlane:
    bounds: tuple[float, float, float, float, float, float]
    materials: frozenset[int] | None
    search_distance: float
    origin: np.ndarray
    normal: np.ndarray

    def selects(self, element: BaseElement, center: np.ndarray) -> bool:
        xmin, xmax, ymin, ymax, zmin, zmax = self.bounds
        if not (
            xmin <= center[0] <= xmax
            and ymin <= center[1] <= ymax
            and zmin <= center[2] <= zmax
        ):
            return False
        if self.materials and element.m_id not in self.materials:
            return False
        distance = abs(float(np.dot(center - self.origin, self.normal)))
        return distance <= self.search_distance


def parse_cutting_control(path: str | Path) -> tuple[list[CuttingPlane], int]:
    tokens = [token for line in clean_control_lines(path) for token in line.split()]
    cursor = 0

    def take(converter, label: str):
        nonlocal cursor
        if cursor >= len(tokens):
            raise ValueError(f"切割控制文件缺少：{label}")
        try:
            value = converter(tokens[cursor])
        except ValueError as error:
            raise ValueError(f"切割控制参数 {label} 无效：{tokens[cursor]}") from error
        cursor += 1
        return value

    maximum_edge = take(float, "最大单元边长")
    if maximum_edge <= 0:
        raise ValueError("最大单元边长必须大于 0")
    search_distance = math.sqrt(3.0) * maximum_edge
    plane_count = take(int, "切割面数量")
    if plane_count <= 0:
        raise ValueError("切割面数量必须大于 0")

    planes: list[CuttingPlane] = []
    for plane_index in range(plane_count):
        material_count = take(int, f"第 {plane_index + 1} 个切割面的材料数量")
        materials = (
            frozenset(
                take(int, f"第 {plane_index + 1} 个切割面的材料号")
                for _ in range(material_count)
            )
            if material_count > 0
            else None
        )
        bounds = tuple(
            take(float, f"第 {plane_index + 1} 个切割面的范围") for _ in range(6)
        )
        if bounds[0] > bounds[1] or bounds[2] > bounds[3] or bounds[4] > bounds[5]:
            raise ValueError(f"第 {plane_index + 1} 个切割面的范围上下限颠倒")
        points = np.asarray(
            [
                [take(float, "切割面点坐标") for _ in range(3)]
                for _ in range(3)
            ],
            dtype=np.float64,
        )
        normal = np.cross(points[1] - points[0], points[2] - points[0])
        length = float(np.linalg.norm(normal))
        if length <= 1e-12:
            raise ValueError(f"第 {plane_index + 1} 个切割面的三个点共线")
        planes.append(
            CuttingPlane(
                bounds,
                materials,
                search_distance,
                points[0],
                normal / length,
            )
        )
    boundary_mode = take(int, "边界处理模式") if cursor < len(tokens) else 0
    if boundary_mode not in (0, 1, 2):
        raise ValueError("边界处理模式只能为 0、1 或 2")
    if cursor != len(tokens):
        raise ValueError("切割控制文件末尾存在无法识别的多余参数")
    return planes, boundary_mode


class NodeRegistry:
    def __init__(self, mesh: Mesh, precision: int = 8):
        self.precision = precision
        self.nodes = list(mesh.nodes)
        self.by_coordinate: dict[tuple[float, float, float], Node] = {}
        for node in mesh.nodes:
            self.by_coordinate.setdefault(self.key(node.coordinates), node)
        self.next_id = max(mesh.node_map, default=0) + 1
        self.new_node_ids: set[int] = set()

    def key(self, coordinates) -> tuple[float, float, float]:
        return tuple(round(float(value), self.precision) for value in coordinates)

    def get(self, coordinates) -> Node:
        key = self.key(coordinates)
        node = self.by_coordinate.get(key)
        if node is None:
            node = Node(self.next_id, *map(float, coordinates))
            self.next_id += 1
            self.nodes.append(node)
            self.by_coordinate[key] = node
            self.new_node_ids.add(node.node_id)
        return node




def _signed_distance(node_id: int, mesh: Mesh, plane: CuttingPlane) -> float:
    node = mesh.node_map[node_id]
    return float(np.dot(np.asarray(node.coordinates) - plane.origin, plane.normal))


def _clip_face(
    face: tuple[int, ...],
    mesh: Mesh,
    registry: NodeRegistry,
    plane: CuttingPlane,
    keep_positive: bool,
    tolerance: float,
) -> tuple[tuple[int, ...], set[int]]:
    output: list[int] = []
    intersections: set[int] = set()

    def inside(distance: float) -> bool:
        return distance >= -tolerance if keep_positive else distance <= tolerance

    previous_id = face[-1]
    previous_distance = _signed_distance(previous_id, mesh, plane)
    previous_inside = inside(previous_distance)
    for current_id in face:
        current_distance = _signed_distance(current_id, mesh, plane)
        current_inside = inside(current_distance)
        if current_inside != previous_inside:
            denominator = previous_distance - current_distance
            if abs(denominator) > 1e-15:
                ratio = previous_distance / denominator
                previous = np.asarray(mesh.node_map[previous_id].coordinates)
                current = np.asarray(mesh.node_map[current_id].coordinates)
                intersection = registry.get(previous + ratio * (current - previous))
                mesh.node_map.setdefault(intersection.node_id, intersection)
                output.append(intersection.node_id)
                intersections.add(intersection.node_id)
        if current_inside:
            output.append(current_id)
            if abs(current_distance) <= tolerance:
                intersections.add(current_id)
        previous_id = current_id
        previous_distance = current_distance
        previous_inside = current_inside
    polygon = _deduplicate_polygon(output)
    return (polygon if len(polygon) >= 3 else ()), intersections


def _sort_plane_polygon(
    node_ids: set[int], mesh: Mesh, normal: np.ndarray
) -> tuple[int, ...]:
    ids = list(node_ids)
    points = np.asarray([mesh.node_map[node_id].coordinates for node_id in ids])
    center = np.mean(points, axis=0)
    reference = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(reference, normal))) > 0.9:
        reference = np.array([0.0, 1.0, 0.0])
    axis_u = np.cross(normal, reference)
    axis_u /= np.linalg.norm(axis_u)
    axis_v = np.cross(normal, axis_u)
    relative = points - center
    angles = np.arctan2(relative @ axis_v, relative @ axis_u)
    return tuple(ids[index] for index in np.argsort(angles))


def _orient_faces_outward(
    faces: tuple[tuple[int, ...], ...], mesh: Mesh
) -> tuple[tuple[int, ...], ...]:
    unique_ids = tuple(dict.fromkeys(node_id for face in faces for node_id in face))
    center = np.mean(
        np.asarray([mesh.node_map[node_id].coordinates for node_id in unique_ids]), axis=0
    )
    oriented: list[tuple[int, ...]] = []
    for face in faces:
        points = np.asarray([mesh.node_map[node_id].coordinates for node_id in face])
        normal = np.zeros(3)
        for index, point in enumerate(points):
            following = points[(index + 1) % len(points)]
            normal += np.cross(point, following)
        if np.dot(normal, np.mean(points, axis=0) - center) < 0:
            face = tuple(reversed(face))
        oriented.append(face)
    return tuple(oriented)


def _validate_convex_polyhedron(
    faces: tuple[tuple[int, ...], ...], mesh: Mesh, tolerance: float
) -> tuple[tuple[int, ...], ...]:
    oriented = _orient_faces_outward(faces, mesh)
    all_ids = set(node_id for face in oriented for node_id in face)
    for face in oriented:
        points = np.asarray([mesh.node_map[node_id].coordinates for node_id in face])
        normal = np.zeros(3)
        for index, point in enumerate(points):
            normal += np.cross(point, points[(index + 1) % len(points)])
        norm = float(np.linalg.norm(normal))
        if norm <= tolerance:
            raise ValueError("单元包含退化面，无法执行可靠的三维切割")
        normal /= norm
        origin = points[0]
        for node_id in all_ids:
            coordinate = np.asarray(mesh.node_map[node_id].coordinates)
            if float(np.dot(coordinate - origin, normal)) > tolerance:
                raise ValueError(
                    "当前切割算法要求单元为凸多面体；检测到凹多面体或面节点顺序异常"
                )
    return oriented


def _clip_polyhedron(
    element: BaseElement,
    mesh: Mesh,
    registry: NodeRegistry,
    plane: CuttingPlane,
    tolerance: float,
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]] | None:
    faces = _validate_convex_polyhedron(
        element.faces(), mesh, max(tolerance, 1e-10)
    )
    unique_ids = set(node_id for face in faces for node_id in face)
    distances = np.asarray(
        [_signed_distance(node_id, mesh, plane) for node_id in unique_ids]
    )
    if not np.any(distances > tolerance) or not np.any(distances < -tolerance):
        return None

    halves: list[tuple[tuple[int, ...], ...]] = []
    for keep_positive in (True, False):
        clipped_faces: list[tuple[int, ...]] = []
        intersection_ids: set[int] = set()
        for face in faces:
            clipped, intersections = _clip_face(
                face, mesh, registry, plane, keep_positive, tolerance
            )
            if clipped:
                clipped_faces.append(clipped)
            intersection_ids.update(intersections)
        if len(intersection_ids) < 3:
            return None
        cap_normal = -plane.normal if keep_positive else plane.normal
        clipped_faces.append(_sort_plane_polygon(intersection_ids, mesh, cap_normal))
        halves.append(_orient_faces_outward(tuple(clipped_faces), mesh))
    return halves[0], halves[1]


def _interface_from_faces(
    original: BaseElement, faces: tuple[tuple[int, ...], ...], mesh: Mesh, e_id: int
) -> PolygonContact:
    original_half = len(original.node_ids) // 2
    original_bottom = original.node_ids[:original_half]
    points = np.asarray([mesh.node_map[node_id].coordinates for node_id in original_bottom])
    normal = np.cross(points[1] - points[0], points[2] - points[0])
    normal /= np.linalg.norm(normal)

    candidates: list[tuple[float, tuple[int, ...]]] = []
    for face in faces:
        coordinates = np.asarray([mesh.node_map[node_id].coordinates for node_id in face])
        face_normal = np.cross(
            coordinates[1] - coordinates[0], coordinates[2] - coordinates[0]
        )
        norm = np.linalg.norm(face_normal)
        if norm > 1e-12:
            alignment = abs(float(np.dot(face_normal / norm, normal)))
            candidates.append((alignment, face))
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) < 2 or candidates[1][0] < 0.9:
        raise ValueError(f"界面单元 {original.e_id} 切割后无法可靠识别上下表面")
    first, second = candidates[0][1], candidates[1][1]
    if len(first) != len(second):
        raise ValueError(f"界面单元 {original.e_id} 切割后的上下表面节点数不一致")
    first_center = np.mean(
        np.asarray([mesh.node_map[node_id].coordinates for node_id in first]), axis=0
    )
    second_center = np.mean(
        np.asarray([mesh.node_map[node_id].coordinates for node_id in second]), axis=0
    )
    bottom, top = (first, second) if np.dot(second_center - first_center, normal) >= 0 else (second, first)
    return PolygonContact(
        e_id,
        60,
        original.c_id,
        original.m_id,
        original.d_id,
        original.f_id,
        tuple(bottom) + tuple(top),
    )


def _make_cut_element(
    original: BaseElement,
    faces: tuple[tuple[int, ...], ...],
    mesh: Mesh,
    e_id: int,
) -> BaseElement:
    if original.is_interface:
        return _interface_from_faces(original, faces, mesh, e_id)
    node_ids = tuple(node_id for face in faces for node_id in face)
    return Polyhedron(
        e_id,
        57,
        original.c_id,
        original.m_id,
        original.d_id,
        original.f_id,
        node_ids,
        faces,
    )


def _point_on_segment(point, start, end, tolerance: float) -> tuple[bool, float]:
    edge = end - start
    length_squared = float(np.dot(edge, edge))
    if length_squared <= tolerance**2:
        return False, 0.0
    parameter = float(np.dot(point - start, edge) / length_squared)
    projection = start + parameter * edge
    return (
        -tolerance <= parameter <= 1.0 + tolerance
        and np.linalg.norm(point - projection) <= tolerance,
        parameter,
    )


def _insert_boundary_nodes(
    element: BaseElement,
    mesh: Mesh,
    new_nodes: list[Node],
    search_distance: float,
    tolerance: float,
) -> BaseElement:
    faces = element.faces()
    center = element.center(mesh.node_map)
    nearby = [
        node
        for node in new_nodes
        if np.linalg.norm(np.asarray(node.coordinates) - center) <= search_distance
    ]
    if not nearby:
        return element
    changed = False
    updated_faces: list[tuple[int, ...]] = []
    for face in faces:
        updated: list[int] = []
        for index, start_id in enumerate(face):
            end_id = face[(index + 1) % len(face)]
            updated.append(start_id)
            start = np.asarray(mesh.node_map[start_id].coordinates)
            end = np.asarray(mesh.node_map[end_id].coordinates)
            insertions: list[tuple[float, int]] = []
            for node in nearby:
                if node.node_id in (start_id, end_id):
                    continue
                on_edge, parameter = _point_on_segment(
                    np.asarray(node.coordinates), start, end, tolerance
                )
                if on_edge and tolerance < parameter < 1.0 - tolerance:
                    insertions.append((parameter, node.node_id))
            if insertions:
                changed = True
                updated.extend(node_id for _, node_id in sorted(set(insertions)))
        updated_faces.append(tuple(updated))
    if not changed:
        return element
    if element.is_interface:
        return _interface_from_faces(element, tuple(updated_faces), mesh, element.e_id)
    faces_tuple = _orient_faces_outward(tuple(updated_faces), mesh)
    return Polyhedron(
        element.e_id,
        57,
        element.c_id,
        element.m_id,
        element.d_id,
        element.f_id,
        tuple(node_id for face in faces_tuple for node_id in face),
        faces_tuple,
    )


def cut_mesh(
    input_path: str,
    control_path: str,
    output_path: str,
    tolerance: float,
    *,
    overwrite: bool = False,
) -> OperationResult:
    source, target = checked_paths(input_path, output_path)
    tolerance = float(tolerance)
    if tolerance <= 0 or not math.isfinite(tolerance):
        raise ValueError("切割容差必须为有限正数")
    planes, boundary_mode = parse_cutting_control(control_path)
    mesh = read_mesh(source)
    registry = NodeRegistry(mesh)
    original_node_count = len(mesh.nodes)
    output_elements: list[BaseElement] = []
    cut_count = 0

    for element in mesh.elements:
        center = element.center(mesh.node_map)
        plane = next((item for item in planes if item.selects(element, center)), None)
        if plane is None:
            output_elements.append(element)
            continue
        clipped = _clip_polyhedron(element, mesh, registry, plane, tolerance)
        if clipped is None:
            output_elements.append(element)
            continue
        positive, negative = clipped
        output_elements.append(_make_cut_element(element, positive, mesh, element.e_id))
        output_elements.append(_make_cut_element(element, negative, mesh, -1))
        cut_count += 1

    mesh.nodes = registry.nodes
    mesh.node_map = {node.node_id: node for node in mesh.nodes}
    if boundary_mode:
        new_nodes = [node for node in mesh.nodes if node.node_id in registry.new_node_ids]
        maximum_distance = max(plane.search_distance for plane in planes)
        output_elements = [
            _insert_boundary_nodes(
                element, mesh, new_nodes, maximum_distance, max(tolerance, 1e-8)
            )
            for element in output_elements
        ]

    for new_id, element in enumerate(output_elements, 1):
        element.e_id = new_id
    mesh.elements = output_elements
    mesh.element_map = {element.e_id: element for element in output_elements}
    mesh.validate_connectivity()
    write_mesh(target, mesh, overwrite=overwrite)
    return OperationResult(
        "三维网格切割",
        f"切割完成：{cut_count} 个原单元被切分，新增 "
        f"{len(mesh.nodes) - original_node_count} 个节点，输出 {len(output_elements)} 个单元。",
        (target,),
        {
            "cut_elements": cut_count,
            "new_nodes": len(mesh.nodes) - original_node_count,
            "output_elements": len(output_elements),
        },
    )
