from __future__ import annotations

import math
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

from aprepost2.domain import BaseElement, Mesh, Node
from aprepost2.io.mesh_io import read_mesh
from aprepost2.io.text import detect_text_encoding
from aprepost2.services.common import OperationResult


@dataclass(frozen=True, slots=True)
class ResultControl:
    node_ids: tuple[int, ...]
    element_ids: tuple[int, ...]
    steps: tuple[int, ...]
    base_node: int | None
    slope: float
    keep_initial_stress: bool
    keep_initial_strain: bool


@dataclass(slots=True)
class NodeHistory:
    node: Node
    values: dict[str, dict[str, np.ndarray]] = field(default_factory=dict)


@dataclass(slots=True)
class ElementHistory:
    element: BaseElement
    values: dict[str, dict[str, np.ndarray]] = field(default_factory=dict)


def parse_result_control(path: str | Path) -> ResultControl:
    source = Path(path)
    encoding = detect_text_encoding(source)
    raw_lines = source.read_text(encoding=encoding).splitlines()
    lines = [
        line.strip()
        for line in raw_lines
        if line.strip() and not line.lstrip().startswith(("#", "//"))
    ]
    nodes: list[int] = []
    elements: list[int] = []
    steps: list[int] = []
    base_node: int | None = None
    slope = 0.0
    keep_initial_stress = True
    keep_initial_strain = True
    index = 0
    while index < len(lines):
        line = lines[index]
        lower = line.lower()
        if "=" not in line:
            index += 1
            continue
        value = line.split("=", 1)[1].strip()
        if "output node number" in lower:
            count = int(value)
            nodes.extend(int(lines[index + offset]) for offset in range(1, count + 1))
            index += count
        elif "output element number" in lower:
            count = int(value)
            elements.extend(int(lines[index + offset]) for offset in range(1, count + 1))
            index += count
        elif "output step number" in lower:
            count = int(value)
            steps.extend(int(lines[index + offset]) for offset in range(1, count + 1))
            index += count
        elif "base node" in lower:
            parsed = int(value)
            base_node = parsed or None
            if base_node:
                nodes.append(base_node)
        elif "podu" in lower:
            slope = float(value)
        elif "initial stress" in lower:
            keep_initial_stress = float(value) != 0
        elif "initial strain" in lower:
            keep_initial_strain = float(value) != 0
        index += 1
    return ResultControl(
        tuple(dict.fromkeys(nodes)),
        tuple(dict.fromkeys(elements)),
        tuple(dict.fromkeys(steps)),
        base_node,
        slope,
        keep_initial_stress,
        keep_initial_strain,
    )


def _frame_sort_key(name: str):
    try:
        return 0, int(name)
    except ValueError:
        return 1, name


def _selected_indices(ids, selected: set[int]) -> dict[int, int]:
    return {
        int(identifier): index
        for index, identifier in enumerate(ids)
        if int(identifier) in selected
    }


def extract_histories(
    hdf5_path: str | Path, mesh: Mesh, control: ResultControl
) -> tuple[dict[int, NodeHistory], dict[int, ElementHistory]]:
    nodes = {
        identifier: NodeHistory(mesh.node_map[identifier])
        for identifier in control.node_ids
        if identifier in mesh.node_map
    }
    elements = {
        identifier: ElementHistory(mesh.element_map[identifier])
        for identifier in control.element_ids
        if identifier in mesh.element_map
    }
    selected_nodes = set(nodes)
    selected_elements = set(elements)
    active_nodes: dict[int, int] = {}
    active_elements: dict[str, dict[int, int]] = {}

    with h5py.File(hdf5_path, "r") as file:
        if "frames" not in file:
            raise ValueError("HDF5 文件缺少 frames 组")
        frames = file["frames"]
        for frame_name in sorted(frames.keys(), key=_frame_sort_key):
            frame = frames[frame_name]
            if "new_topology/node_ids" in frame:
                active_nodes = _selected_indices(
                    frame["new_topology/node_ids"][:], selected_nodes
                )
            node_variables = {
                "displacement": "node_vars/displacement",
                "poressure": "node_vars/poressure",
                "acceleration": "node_vars/acceleration",
                "velocity": "node_vars/velocity",
            }
            for variable, dataset_path in node_variables.items():
                if dataset_path not in frame:
                    continue
                dataset = frame[dataset_path]
                for node_id, data_index in active_nodes.items():
                    if data_index < dataset.shape[0]:
                        nodes[node_id].values.setdefault(frame_name, {})[variable] = np.asarray(
                            dataset[data_index], dtype=np.float64
                        )

            if "parts" not in frame:
                continue
            for part_name in frame["parts"]:
                part = frame[f"parts/{part_name}"]
                if "elem_ids" in part:
                    active_elements[part_name] = _selected_indices(
                        part["elem_ids"][:], selected_elements
                    )
                indices = active_elements.get(part_name, {})
                variables = {
                    "stress": "elem_vars/stress",
                    "strain": "elem_vars/strain",
                    "interface_stress": "elem_vars/interface_stress",
                    "interface_relative_displacement": "elem_vars/interface_relative_displacement",
                }
                for variable, dataset_path in variables.items():
                    if dataset_path not in part:
                        continue
                    dataset = part[dataset_path]
                    canonical = (
                        "stress"
                        if variable in {"stress", "interface_stress"}
                        else "strain"
                    )
                    for element_id, data_index in indices.items():
                        if data_index < dataset.shape[0]:
                            elements[element_id].values.setdefault(frame_name, {})[
                                canonical
                            ] = np.asarray(dataset[data_index], dtype=np.float64)
    return nodes, elements


def _subtract_base_node(
    histories: dict[int, NodeHistory], base_node: int | None
) -> None:
    if not base_node or base_node not in histories:
        return
    base = histories[base_node]
    for node_id, history in histories.items():
        if node_id == base_node:
            continue
        for step, variables in history.values.items():
            base_displacement = base.values.get(step, {}).get("displacement")
            if base_displacement is not None and "displacement" in variables:
                length = min(len(variables["displacement"]), len(base_displacement))
                variables["displacement"][:length] -= base_displacement[:length]


def _pad(values: np.ndarray | None, size: int) -> list[float]:
    if values is None:
        return [np.nan] * size
    flattened = np.ravel(values).astype(float).tolist()
    return (flattened + [np.nan] * size)[:size]


def _node_frame(history: NodeHistory) -> pd.DataFrame:
    dimension = max(
        (
            len(np.ravel(variables["displacement"]))
            for variables in history.values.values()
            if "displacement" in variables
        ),
        default=3,
    )
    dimension = 2 if dimension == 2 else 3
    rows: list[list] = []
    for step in sorted(history.values, key=_frame_sort_key):
        variables = history.values[step]
        displacement = _pad(variables.get("displacement"), dimension)
        velocity = _pad(variables.get("velocity"), dimension)
        acceleration = _pad(variables.get("acceleration"), dimension)
        pore = _pad(variables.get("poressure"), 1)[0]
        rows.append([step, *acceleration, *velocity, *displacement, pore])
    axes = ("x", "y") if dimension == 2 else ("x", "y", "z")
    columns = (
        ["step"]
        + [f"acc{axis}" for axis in axes]
        + [f"vel{axis}" for axis in axes]
        + [f"disp{axis}" for axis in axes]
        + ["pore"]
    )
    return pd.DataFrame(rows, columns=columns)


def _solid_3d_derived(stress: np.ndarray, strain: np.ndarray, slope: float) -> list:
    signed_stress = -stress
    tensor = np.array(
        [
            [signed_stress[0], signed_stress[3], signed_stress[5]],
            [signed_stress[3], signed_stress[1], signed_stress[4]],
            [signed_stress[5], signed_stress[4], signed_stress[2]],
        ]
    )
    principal_stress = np.linalg.eigvalsh(tensor)[::-1]
    p = float(np.mean(signed_stress[:3]))
    j2 = (
        (signed_stress[0] - signed_stress[1]) ** 2
        + (signed_stress[0] - signed_stress[2]) ** 2
        + (signed_stress[1] - signed_stress[2]) ** 2
    ) / 6 + float(np.sum(signed_stress[3:6] ** 2))
    q = math.sqrt(max(0.0, 3 * j2))
    signed_strain = -strain
    strain_tensor = np.array(
        [
            [signed_strain[0], signed_strain[3] / 2, signed_strain[5] / 2],
            [signed_strain[3] / 2, signed_strain[1], signed_strain[4] / 2],
            [signed_strain[5] / 2, signed_strain[4] / 2, signed_strain[2]],
        ]
    )
    principal_strain = np.linalg.eigvalsh(strain_tensor)[::-1]
    eps_v = float(np.sum(signed_strain[:3]))
    mean_strain = eps_v / 3
    deviator = strain_tensor - np.eye(3) * mean_strain
    eps_q = math.sqrt(max(0.0, 2 / 3 * float(np.sum(deviator * deviator))))
    if slope:
        cosine = slope / math.sqrt(slope * slope + 1)
        sine = 1 / math.sqrt(slope * slope + 1)
        d1 = (
            signed_stress[1] * sine**2
            + signed_stress[0] * cosine**2
            + 2 * signed_stress[3] * sine * cosine
        )
        d2 = signed_stress[2]
        d3 = (
            signed_stress[0] * sine**2
            + signed_stress[1] * cosine**2
            - 2 * signed_stress[3] * sine * cosine
        )
    else:
        d1 = d2 = d3 = 0.0
    dynamic_shear = float(principal_strain[0] - principal_strain[2])
    return [
        p, q, *principal_stress, d1, d2, d3,
        eps_v, eps_q, *principal_strain, dynamic_shear,
    ]


def _solid_2d_derived(stress: np.ndarray, strain: np.ndarray, slope: float) -> list:
    signed_stress = -stress
    tensor = np.array(
        [
            [signed_stress[0], signed_stress[3], 0.0],
            [signed_stress[3], signed_stress[1], 0.0],
            [0.0, 0.0, signed_stress[2]],
        ]
    )
    principal_stress = np.linalg.eigvalsh(tensor)[::-1]
    p = float(np.mean(signed_stress[:3]))
    j2 = (
        (signed_stress[0] - signed_stress[1]) ** 2
        + (signed_stress[0] - signed_stress[2]) ** 2
        + (signed_stress[1] - signed_stress[2]) ** 2
    ) / 6 + signed_stress[3] ** 2
    q = math.sqrt(max(0.0, 3 * j2))
    signed_strain = -strain
    strain_tensor = np.array(
        [
            [signed_strain[0], signed_strain[2] / 2, 0.0],
            [signed_strain[2] / 2, signed_strain[1], 0.0],
            [0.0, 0.0, 0.0],
        ]
    )
    principal_strain = np.linalg.eigvalsh(strain_tensor)[::-1]
    eps_v = float(signed_strain[0] + signed_strain[1])
    mean_strain = eps_v / 3
    deviator = strain_tensor - np.eye(3) * mean_strain
    eps_q = math.sqrt(max(0.0, 2 / 3 * float(np.sum(deviator * deviator))))
    if slope:
        cosine = slope / math.sqrt(slope * slope + 1)
        sine = 1 / math.sqrt(slope * slope + 1)
        d1 = (
            signed_stress[1] * sine**2
            + signed_stress[0] * cosine**2
            + 2 * signed_stress[3] * sine * cosine
        )
        d2 = signed_stress[2]
        d3 = (
            signed_stress[0] * sine**2
            + signed_stress[1] * cosine**2
            - 2 * signed_stress[3] * sine * cosine
        )
    else:
        d1 = d2 = d3 = 0.0
    dynamic_shear = float(principal_strain[0] - principal_strain[2])
    return [
        p, q, *principal_stress, d1, d2, d3,
        eps_v, eps_q, *principal_strain, dynamic_shear,
    ]


def _element_frame(history: ElementHistory, control: ResultControl) -> pd.DataFrame:
    records: list[dict[str, float | str]] = []
    ordered_steps = sorted(history.values, key=_frame_sort_key)
    initial_stress = None
    initial_strain = None
    for step in ordered_steps:
        values = history.values[step]
        if initial_stress is None and "stress" in values:
            initial_stress = values["stress"].copy()
        if initial_strain is None and "strain" in values:
            initial_strain = values["strain"].copy()
        stress = values.get("stress")
        strain = values.get("strain")
        if stress is not None and not control.keep_initial_stress:
            stress = stress - initial_stress
        if strain is not None and not control.keep_initial_strain:
            strain = strain - initial_strain
        record: dict[str, float | str] = {"step": step}
        for index, value in enumerate(np.ravel(stress) if stress is not None else ()):
            record[f"stress_{index + 1}"] = float(value)
        for index, value in enumerate(np.ravel(strain) if strain is not None else ()):
            record[f"strain_{index + 1}"] = float(value)
        if (
            history.element.is_3d_solid
            and stress is not None
            and strain is not None
            and np.size(stress) >= 6
            and np.size(strain) >= 6
        ):
            derived = _solid_3d_derived(
                np.ravel(stress)[:6], np.ravel(strain)[:6], control.slope
            )
            names = (
                "p", "q", "sigma_1", "sigma_2", "sigma_3",
                "sigma_d1", "sigma_d2", "sigma_d3",
                "eps_v", "eps_q", "eps_1", "eps_2", "eps_3",
                "dynamic_shear_strain",
            )
            record.update(zip(names, derived))
        elif (
            history.element.is_2d_solid
            and stress is not None
            and strain is not None
            and np.size(stress) >= 4
            and np.size(strain) >= 3
        ):
            derived = _solid_2d_derived(
                np.ravel(stress)[:4], np.ravel(strain)[:3], control.slope
            )
            names = (
                "p", "q", "sigma_1", "sigma_2", "sigma_3",
                "sigma_d1", "sigma_d2", "sigma_d3",
                "eps_v", "eps_q", "eps_1", "eps_2", "eps_3",
                "dynamic_shear_strain",
            )
            record.update(zip(names, derived))
        records.append(record)
    frame = pd.DataFrame(records)
    if "dynamic_shear_strain" in frame and not frame.empty:
        frame["dynamic_shear_strain"] -= frame["dynamic_shear_strain"].iloc[0]
    return frame


def _atomic_excel(target: Path, sheets: dict[str, pd.DataFrame]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.stem}.", suffix=".xlsx"
    )
    os.close(descriptor)
    try:
        with pd.ExcelWriter(temporary, engine="openpyxl") as writer:
            if not sheets:
                pd.DataFrame({"message": ["没有有效数据"]}).to_excel(
                    writer, sheet_name="empty", index=False
                )
            for name, frame in sheets.items():
                frame.to_excel(writer, sheet_name=str(name)[:31], index=False)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _write_text_outputs(
    output_directory: Path,
    node_frames: dict[int, pd.DataFrame],
    element_frames: dict[int, pd.DataFrame],
    mesh: Mesh,
    requested_steps: tuple[int, ...],
) -> list[Path]:
    outputs: list[Path] = []
    for node_id, frame in node_frames.items():
        path = output_directory / f"{node_id}.node"
        frame.to_csv(path, sep="\t", index=False, na_rep="")
        outputs.append(path)
    for element_id, frame in element_frames.items():
        path = output_directory / f"{element_id}.ele"
        frame.to_csv(path, sep="\t", index=False, na_rep="")
        outputs.append(path)

    for step in requested_steps:
        step_name = str(step)
        node_rows = []
        for node_id, frame in node_frames.items():
            selected = frame[frame["step"].astype(str) == step_name]
            if not selected.empty:
                node_rows.append({"node_id": node_id, **selected.iloc[0].to_dict()})
        element_rows = []
        for element_id, frame in element_frames.items():
            selected = frame[frame["step"].astype(str) == step_name]
            if not selected.empty:
                center = mesh.element_map[element_id].center(mesh.node_map)
                element_rows.append(
                    {
                        "element_id": element_id,
                        "center_x": center[0],
                        "center_y": center[1],
                        "center_z": center[2],
                        **selected.iloc[0].to_dict(),
                    }
                )
        node_path = output_directory / f"step_{step_name}_node_data.txt"
        element_path = output_directory / f"step_{step_name}_element_data.txt"
        pd.DataFrame(node_rows).to_csv(node_path, sep="\t", index=False)
        pd.DataFrame(element_rows).to_csv(element_path, sep="\t", index=False)
        outputs.extend((node_path, element_path))

    node_max = []
    for node_id, frame in node_frames.items():
        numeric = frame.select_dtypes(include=[np.number]).drop(columns=["step"], errors="ignore")
        row = {"node_id": node_id}
        for column in numeric:
            values = numeric[column]
            if column.startswith(("acc", "vel", "disp")):
                values = -values
            row[f"max_{column}"] = values.max()
            row[f"min_{column}"] = values.min()
        node_max.append(row)
    element_max = []
    for element_id, frame in element_frames.items():
        numeric = frame.select_dtypes(include=[np.number]).drop(columns=["step"], errors="ignore")
        row = {"element_id": element_id}
        for column in numeric:
            values = numeric[column]
            if column.startswith(("stress_", "strain_")):
                values = -values
            row[f"max_{column}"] = values.max()
            row[f"min_{column}"] = values.min()
        element_max.append(row)
    node_max_path = output_directory / "max_node_step.dat"
    element_max_path = output_directory / "max_element_step.dat"
    pd.DataFrame(node_max).to_csv(node_max_path, sep="\t", index=False)
    pd.DataFrame(element_max).to_csv(element_max_path, sep="\t", index=False)
    outputs.extend((node_max_path, element_max_path))
    return outputs


def read_hdf5_results(
    control_path: str,
    hdf5_path: str,
    output_prefix: str,
    mesh_path: str,
    *,
    overwrite: bool = False,
) -> OperationResult:
    control = parse_result_control(control_path)
    mesh = read_mesh(mesh_path)
    histories, element_histories = extract_histories(hdf5_path, mesh, control)
    _subtract_base_node(histories, control.base_node)
    node_frames = {node_id: _node_frame(history) for node_id, history in histories.items()}
    element_frames = {
        element_id: _element_frame(history, control)
        for element_id, history in element_histories.items()
    }
    prefix = Path(output_prefix).expanduser().resolve()
    output_directory = prefix.parent
    output_directory.mkdir(parents=True, exist_ok=True)
    node_excel = Path(f"{prefix}_node_schedule.xlsx")
    element_excel = Path(f"{prefix}_element_schedule.xlsx")
    detail_directory = prefix.parent / f"{prefix.name}_details"
    existing = [
        path for path in (node_excel, element_excel, detail_directory) if path.exists()
    ]
    if existing and not overwrite:
        raise FileExistsError(
            "以下输出已存在，请更换前缀或明确允许覆盖："
            + "，".join(str(path) for path in existing)
        )
    detail_directory.mkdir(parents=True, exist_ok=True)
    _atomic_excel(node_excel, {str(key): value for key, value in node_frames.items()})
    _atomic_excel(
        element_excel, {str(key): value for key, value in element_frames.items()}
    )
    text_outputs = _write_text_outputs(
        detail_directory, node_frames, element_frames, mesh, control.steps
    )
    return OperationResult(
        "读取 HDF5 结果",
        f"结果读取完成：{len(node_frames)} 个节点、{len(element_frames)} 个单元。",
        (node_excel, element_excel, *text_outputs),
        {"nodes": len(node_frames), "elements": len(element_frames)},
    )
