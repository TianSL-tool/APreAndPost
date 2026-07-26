from __future__ import annotations

import math
from time import perf_counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from aprepost2.domain import BaseElement, Mesh, Node
from aprepost2.domain.element import (
    Polyhedron,
    PolygonContact,
)
from aprepost2.domain.elements.base import deduplicate_polygon
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
    boundary_mode = take(int, "边界处理模式") if cursor < len(tokens) else 1
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
        self.edge_intersections: dict[tuple[int, int], set[int]] = {}

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

    def register_edge_intersection(
        self, start_id: int, end_id: int, node_id: int
    ) -> None:
        if node_id in (start_id, end_id):
            return
        key = tuple(sorted((int(start_id), int(end_id))))
        self.edge_intersections.setdefault(key, set()).add(int(node_id))




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
                registry.register_edge_intersection(
                    previous_id, current_id, intersection.node_id
                )
                output.append(intersection.node_id)
                intersections.add(intersection.node_id)
        if current_inside:
            output.append(current_id)
            if abs(current_distance) <= tolerance:
                intersections.add(current_id)
        previous_id = current_id
        previous_distance = current_distance
        previous_inside = current_inside
    polygon = deduplicate_polygon(output)
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


def _face_normal(face: tuple[int, ...], mesh: Mesh) -> np.ndarray:
    points = np.asarray([mesh.node_map[node_id].coordinates for node_id in face])
    normal = np.zeros(3)
    for index, point in enumerate(points):
        normal += np.cross(point, points[(index + 1) % len(points)])
    return normal


def _split_face_between_nodes(
    face: tuple[int, ...],
    first_index: int,
    second_index: int,
    mesh: Mesh,
    tolerance: float,
) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    count = len(face)
    if count < 4:
        return None
    if first_index > second_index:
        first_index, second_index = second_index, first_index
    if second_index == first_index + 1 or (first_index == 0 and second_index == count - 1):
        return None
    first_face = face[first_index : second_index + 1]
    second_face = face[second_index:] + face[: first_index + 1]
    if (
        len(first_face) >= 3
        and len(second_face) >= 3
        and np.linalg.norm(_face_normal(first_face, mesh)) > tolerance
        and np.linalg.norm(_face_normal(second_face, mesh)) > tolerance
    ):
        return first_face, second_face
    return None


def _split_faces_along_cutting_planes(
    faces: tuple[tuple[int, ...], ...],
    mesh: Mesh,
    planes: tuple[CuttingPlane, ...],
    tolerance: float,
) -> tuple[tuple[int, ...], ...]:
    pending = list(faces)
    refined: list[tuple[int, ...]] = []
    guard = 0
    while pending:
        guard += 1
        if guard > 10000:
            raise ValueError("面片沿切割面拆分次数过多，可能存在异常面拓扑")
        face = pending.pop(0)
        split_faces = None
        for plane in planes:
            on_plane = [
                index
                for index, node_id in enumerate(face)
                if abs(_signed_distance(node_id, mesh, plane)) <= tolerance
            ]
            if len(on_plane) != 2:
                continue
            split_faces = _split_face_between_nodes(
                face, on_plane[0], on_plane[1], mesh, tolerance
            )
            if split_faces is not None:
                break
        if split_faces is None:
            refined.append(face)
        else:
            pending[:0] = list(split_faces)
    return tuple(refined)


def _validate_convex_polyhedron(
    faces: tuple[tuple[int, ...], ...],
    mesh: Mesh,
    tolerance: float,
    element_id: int | None = None,
) -> tuple[tuple[int, ...], ...]:
    oriented = _orient_faces_outward(faces, mesh)
    all_ids = set(node_id for face in oriented for node_id in face)
    label = f"单元 {element_id}" if element_id is not None else "单元"
    for face_index, face in enumerate(oriented, 1):
        points = np.asarray([mesh.node_map[node_id].coordinates for node_id in face])
        normal = np.zeros(3)
        for index, point in enumerate(points):
            normal += np.cross(point, points[(index + 1) % len(points)])
        norm = float(np.linalg.norm(normal))
        if norm <= tolerance:
            raise ValueError(f"{label} 包含退化面 {face_index}，无法执行可靠的三维切割")
        normal /= norm
        origin = points[0]
        face_ids = set(face)
        for node_id in all_ids:
            if node_id in face_ids:
                continue
            coordinate = np.asarray(mesh.node_map[node_id].coordinates)
            distance = float(np.dot(coordinate - origin, normal))
            if distance > tolerance:
                raise ValueError(
                    f"当前切割算法要求单元为凸多面体；{label} 的面 {face_index} "
                    f"检测到节点 {node_id} 位于外侧，距离 {distance:.6g}，"
                    "可能是凹多面体或面节点顺序异常"
                )
    return oriented


def _clip_polyhedron(
    element: BaseElement,
    mesh: Mesh,
    registry: NodeRegistry,
    plane: CuttingPlane,
    tolerance: float,
) -> tuple[tuple[tuple[int, ...], ...], tuple[tuple[int, ...], ...]] | None:
    raw_faces = element.faces()
    if not raw_faces:
        return None
    faces = _validate_convex_polyhedron(
        raw_faces, mesh, max(tolerance, 1e-10), element.e_id
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
    return PolygonContact.from_surfaces(
        e_id,
        60,
        original.c_id,
        original.m_id,
        original.d_id,
        original.f_id,
        tuple(bottom),
        tuple(top),
    )


def _make_cut_element(
    original: BaseElement,
    faces: tuple[tuple[int, ...], ...],
    mesh: Mesh,
    e_id: int,
    planes: tuple[CuttingPlane, ...],
    tolerance: float,
) -> BaseElement:
    if original.is_interface:
        return _interface_from_faces(original, faces, mesh, e_id)
    faces = _orient_faces_outward(
        _split_faces_along_cutting_planes(faces, mesh, planes, tolerance), mesh
    )
    return Polyhedron.from_faces(
        e_id,
        57,
        original.c_id,
        original.m_id,
        original.d_id,
        original.f_id,
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
    edge_intersections: dict[tuple[int, int], set[int]],
    planes: tuple[CuttingPlane, ...],
    tolerance: float,
) -> BaseElement:
    faces = element.faces()
    changed = False
    updated_faces: list[tuple[int, ...]] = []
    for face in faces:
        updated: list[int] = []
        inserted_in_face: list[int] = []
        for index, start_id in enumerate(face):
            end_id = face[(index + 1) % len(face)]
            updated.append(start_id)
            start = np.asarray(mesh.node_map[start_id].coordinates)
            end = np.asarray(mesh.node_map[end_id].coordinates)
            insertions: list[tuple[float, int]] = []
            edge_key = tuple(sorted((start_id, end_id)))
            for node_id in edge_intersections.get(edge_key, ()):
                if node_id in (start_id, end_id):
                    continue
                on_edge, parameter = _point_on_segment(
                    np.asarray(mesh.node_map[node_id].coordinates), start, end, tolerance
                )
                if on_edge and tolerance < parameter < 1.0 - tolerance:
                    insertions.append((parameter, node_id))
            if insertions:
                changed = True
                inserted_ids = [node_id for _, node_id in sorted(set(insertions))]
                updated.extend(inserted_ids)
                inserted_in_face.extend(inserted_ids)
        if len(inserted_in_face) == 2:
            first, second = inserted_in_face
            first_index = updated.index(first)
            second_index = updated.index(second)
            if first_index > second_index:
                first, second = second, first
                first_index, second_index = second_index, first_index
            first_path = updated[first_index : second_index + 1]
            second_path = updated[second_index:] + updated[: first_index + 1]
            if len(first_path) >= 3 and len(second_path) >= 3:
                updated_faces.append(tuple(first_path))
                updated_faces.append(tuple(second_path))
                continue
        updated_faces.append(tuple(updated))
    if not changed:
        return element
    if element.is_interface:
        return _interface_from_faces(element, tuple(updated_faces), mesh, element.e_id)
    faces_tuple = _orient_faces_outward(
        _split_faces_along_cutting_planes(tuple(updated_faces), mesh, planes, tolerance), mesh
    )
    return Polyhedron.from_faces(
        element.e_id,
        57,
        element.c_id,
        element.m_id,
        element.d_id,
        element.f_id,
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
    started_at = perf_counter()
    last_mark = started_at
    log_lines: list[str] = []

    def mark(stage: str) -> None:
        nonlocal last_mark
        now = perf_counter()
        log_lines.append(
            f"{stage}：耗时 {now - last_mark:.3f} 秒，累计 {now - started_at:.3f} 秒"
        )
        last_mark = now

    source, target = checked_paths(input_path, output_path)
    tolerance = float(tolerance)
    if tolerance <= 0 or not math.isfinite(tolerance):
        raise ValueError("切割容差必须为有限正数")
    planes, boundary_mode = parse_cutting_control(control_path)
    mark(f"读取切割控制文件，切割面 {len(planes)} 个，边界处理模式 {boundary_mode}")
    mesh = read_mesh(source)
    mark(f"读取网格，节点 {len(mesh.nodes)} 个，单元 {len(mesh.elements)} 个")
    registry = NodeRegistry(mesh)
    original_node_count = len(mesh.nodes)
    output_elements: list[BaseElement] = []
    selected_count = 0
    cut_count = 0

    for element in mesh.elements:
        center = element.center(mesh.node_map)
        plane = next((item for item in planes if item.selects(element, center)), None)
        if plane is None:
            output_elements.append(element)
            continue
        selected_count += 1
        clipped = _clip_polyhedron(element, mesh, registry, plane, tolerance)
        if clipped is None:
            output_elements.append(element)
            continue
        positive, negative = clipped
        output_elements.append(
            _make_cut_element(
                element,
                positive,
                mesh,
                element.e_id,
                tuple(planes),
                max(tolerance, 1e-8),
            )
        )
        output_elements.append(
            _make_cut_element(
                element,
                negative,
                mesh,
                -1,
                tuple(planes),
                max(tolerance, 1e-8),
            )
        )
        cut_count += 1
    mark(f"筛选与切割，命中 {selected_count} 个单元，切分 {cut_count} 个原单元")

    mesh.nodes = registry.nodes
    mesh.node_map = {node.node_id: node for node in mesh.nodes}
    boundary_updates = 0
    if boundary_mode:
        updated_elements: list[BaseElement] = []
        for element in output_elements:
            updated = _insert_boundary_nodes(
                element,
                mesh,
                registry.edge_intersections,
                tuple(planes),
                max(tolerance, 1e-8),
            )
            if updated is not element:
                boundary_updates += 1
            updated_elements.append(updated)
        output_elements = updated_elements
        mark(
            f"边界协调，检查 {len(output_elements)} 个单元，"
            f"边索引 {len(registry.edge_intersections)} 条，更新 {boundary_updates} 个单元"
        )
    else:
        mark("边界协调，控制文件明确关闭，跳过")

    for new_id, element in enumerate(output_elements, 1):
        element.e_id = new_id
    mesh.elements = output_elements
    mesh.element_map = {element.e_id: element for element in output_elements}
    mesh.validate_connectivity()
    orientation_errors: list[str] = []
    for element in output_elements:
        if not element.is_polyhedron:
            continue
        for face_index, reason in element.face_orientation_violations(
            mesh.node_map, max(tolerance, 1e-10)
        ):
            orientation_errors.append(f"单元 {element.e_id} 面 {face_index}：{reason}")
            if len(orientation_errors) >= 10:
                break
        if len(orientation_errors) >= 10:
            break
    if orientation_errors:
        raise ValueError(
            "输出多面体面节点顺序不满足右手定则外法向要求："
            + "；".join(orientation_errors)
        )
    mark(f"重编号、连通性和面法向检查，输出单元 {len(output_elements)} 个")
    write_mesh(target, mesh, overwrite=overwrite)
    mark(f"写出网格，新增节点 {len(mesh.nodes) - original_node_count} 个")
    return OperationResult(
        "三维网格切割",
        f"切割完成：{cut_count} 个原单元被切分，新增 "
        f"{len(mesh.nodes) - original_node_count} 个节点，输出 {len(output_elements)} 个单元。",
        (target,),
        {
            "cut_elements": cut_count,
            "new_nodes": len(mesh.nodes) - original_node_count,
            "output_elements": len(output_elements),
            "boundary_updates": boundary_updates,
        },
        tuple(log_lines),
    )
