from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from aprepost2.io.mesh_io import read_mesh
from aprepost2.io.text import clean_control_lines
from aprepost2.services.common import OperationResult


@dataclass(slots=True)
class SearchPoint:
    label: str
    point_id: float
    coordinates: tuple[float, float, float]
    materials: tuple[int, ...] = ()


def _read_points(path: str, *, with_materials: bool) -> list[SearchPoint]:
    lines = clean_control_lines(path)
    if not lines:
        raise ValueError("检索控制文件为空")
    count = int(lines[0].split()[0])
    if len(lines) < count + 1:
        raise ValueError(f"控制文件声明 {count} 个测点，但数据行不足")
    points: list[SearchPoint] = []
    for index, line in enumerate(lines[1 : count + 1], 1):
        parts = line.split()
        minimum = 6 if with_materials else 5
        if len(parts) < minimum:
            raise ValueError(f"第 {index} 个测点的数据列不足")
        points.append(
            SearchPoint(
                parts[0],
                float(parts[1]),
                tuple(float(value) for value in parts[2:5]),
                tuple(int(float(value)) for value in parts[5:]) if with_materials else (),
            )
        )
    return points


def _nearest_indices(data: np.ndarray, queries: np.ndarray) -> np.ndarray:
    try:
        from scipy.spatial import cKDTree

        return np.asarray(cKDTree(data).query(queries, workers=-1)[1], dtype=np.int64)
    except ImportError:
        indices = np.empty(len(queries), dtype=np.int64)
        for index, query in enumerate(queries):
            indices[index] = np.argmin(np.sum((data - query) ** 2, axis=1))
        return indices


def _write_excel_atomic(frame: pd.DataFrame, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(
            dir=target.parent, prefix=f".{target.stem}.", suffix=".xlsx"
        )
        os.close(descriptor)
        frame.to_excel(temporary_path, index=False, engine="openpyxl")
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


def search_nearest_nodes(
    mesh_path: str, control_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    target = Path(output_path).expanduser().resolve()
    if target.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在：{target}")
    mesh = read_mesh(mesh_path)
    points = _read_points(control_path, with_materials=False)
    node_coordinates = mesh.coordinates_array()
    query_coordinates = np.asarray([point.coordinates for point in points])
    indices = _nearest_indices(node_coordinates, query_coordinates)
    records = []
    for point, index in zip(points, indices):
        node = mesh.nodes[int(index)]
        records.append(
            [
                point.label,
                point.point_id,
                node.node_id,
                *point.coordinates,
                node.x,
                node.y,
                node.z,
            ]
        )
    frame = pd.DataFrame(
        records,
        columns=[
            "测点label",
            "测点id",
            "节点id",
            "测点坐标x",
            "测点坐标y",
            "测点坐标z",
            "节点坐标x",
            "节点坐标y",
            "节点坐标z",
        ],
    )
    _write_excel_atomic(frame, target)
    return OperationResult(
        "检索最近节点",
        f"已完成 {len(points)} 个测点的最近节点检索。",
        (target,),
        {"query_points": len(points), "nodes": len(mesh.nodes)},
    )


def search_nearest_elements(
    mesh_path: str, control_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    target = Path(output_path).expanduser().resolve()
    if target.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在：{target}")
    mesh = read_mesh(mesh_path)
    points = _read_points(control_path, with_materials=True)
    centers = np.asarray(
        [element.center(mesh.node_map) for element in mesh.elements], dtype=np.float64
    )
    material_indices: dict[int, list[int]] = {}
    for index, element in enumerate(mesh.elements):
        material_indices.setdefault(element.m_id, []).append(index)

    records: list[list] = [None] * len(points)
    query_groups: dict[tuple[int, ...], list[int]] = {}
    for point_index, point in enumerate(points):
        material_key = tuple(sorted(set(point.materials)))
        query_groups.setdefault(material_key, []).append(point_index)

    for material_key, point_indices in query_groups.items():
        candidates = sorted(
            {
                index
                for material in material_key
                for index in material_indices.get(material, ())
            }
        )
        if not candidates:
            point = points[point_indices[0]]
            raise ValueError(
                f"测点 {point.label} 指定的材料号在网格中均不存在：{point.materials}"
            )
        candidate_array = np.asarray(candidates, dtype=np.int64)
        queries = np.asarray([points[index].coordinates for index in point_indices])
        local_indices = _nearest_indices(centers[candidate_array], queries)
        for point_index, local_index in zip(point_indices, local_indices):
            point = points[point_index]
            element_index = int(candidate_array[int(local_index)])
            element = mesh.elements[element_index]
            center = centers[element_index]
            records[point_index] = [
                point.label,
                point.point_id,
                element.e_id,
                *point.coordinates,
                *center,
                element.m_id,
            ]
    frame = pd.DataFrame(
        records,
        columns=[
            "测点label",
            "测点id",
            "单元id",
            "测点坐标x",
            "测点坐标y",
            "测点坐标z",
            "单元形心x",
            "单元形心y",
            "单元形心z",
            "单元材料号",
        ],
    )
    _write_excel_atomic(frame, target)
    return OperationResult(
        "检索最近单元",
        f"已完成 {len(points)} 个测点的最近单元检索。",
        (target,),
        {"query_points": len(points), "elements": len(mesh.elements)},
    )
