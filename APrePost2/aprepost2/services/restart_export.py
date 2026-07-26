from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

from aprepost2.services.common import OperationResult, checked_paths


ELEMENT_INFO_COLUMNS = (
    "element_id",
    "material_type",
    "gauss_points",
    "stress_components",
    "strain_components",
    "state_variables",
)


def _parse_element_ids(value: str) -> list[int]:
    source = Path(value).expanduser()
    if source.is_file():
        text = source.read_text(encoding="utf-8-sig")
    else:
        text = value

    cleaned_lines = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].split("//", 1)[0]
        cleaned_lines.append(line)
    ids = [int(token) for token in re.findall(r"[-+]?\d+", "\n".join(cleaned_lines))]
    if len(ids) >= 2 and ids[0] == len(ids) - 1:
        ids = ids[1:]
    if not ids:
        raise ValueError("未读取到单元号，请输入逗号/空格分隔的单元号，或填写单元号文本文件路径")

    unique_ids: list[int] = []
    seen: set[int] = set()
    for element_id in ids:
        if element_id not in seen:
            unique_ids.append(element_id)
            seen.add(element_id)
    return unique_ids


def _resolve_restart_group(file: h5py.File, restart_step: str) -> h5py.Group:
    if "output_for_restart" not in file:
        raise ValueError("HDF5 文件缺少 output_for_restart 组，当前功能只读取重启动 H5 结构")
    root = file["output_for_restart"]
    step = restart_step.strip()
    if not step or step.lower() == "auto":
        names = list(root.keys())
        if len(names) != 1:
            raise ValueError(
                "restart_step=auto 仅适用于只有一个重启动步的文件；请明确填写步号"
            )
        step = names[0]
    if step not in root:
        available = ", ".join(root.keys())
        raise ValueError(f"output_for_restart 下不存在步 {step}；可用步为：{available}")
    return root[step]


def _validate_restart_arrays(
    element_info: np.ndarray,
    datasets: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    if element_info.ndim != 2 or element_info.shape[1] != 6:
        raise ValueError(
            "element_info 必须是 N x 6 数组：单元号、单元材料类型、高斯点数、应力分量数、应变分量数、内变量个数"
        )
    counts = element_info[:, 2:6].astype(np.int64, copy=False)
    if np.any(counts < 0):
        raise ValueError("element_info 中高斯点数或分量个数不能为负")
    component_columns = {
        "stress": 1,
        "strain": 2,
        "constitutive_variables": 3,
    }
    offsets: dict[str, np.ndarray] = {}
    mismatches: list[str] = []
    for name, column_index in component_columns.items():
        if name not in datasets:
            continue
        data_counts = counts[:, 0] * counts[:, column_index]
        expected = int(np.sum(data_counts))
        actual = int(datasets[name].size)
        if actual != expected:
            mismatches.append(f"{name} {actual}/{expected}")
        offsets[name] = np.concatenate(([0], np.cumsum(data_counts)))
    if mismatches:
        raise ValueError("重启动数组长度与 element_info 不一致：" + "，".join(mismatches))
    return offsets


def _write_restart_excel_atomic(
    data: pd.DataFrame, summary: pd.DataFrame, target: Path
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(
            dir=target.parent, prefix=f".{target.stem}.", suffix=".xlsx"
        )
        os.close(descriptor)
        with pd.ExcelWriter(temporary_path, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name="gauss_point_data", index=False)
            summary.to_excel(writer, sheet_name="selected_elements", index=False)
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)


def export_restart_element_gauss_data(
    hdf5_path: str,
    restart_step: str,
    element_ids: str,
    output_path: str,
    *,
    overwrite: bool = False,
) -> OperationResult:
    if not output_path.lower().endswith(".xlsx"):
        output_path += ".xlsx"
    source, target = checked_paths(hdf5_path, output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在：{target}")

    requested_ids = _parse_element_ids(element_ids)
    requested_set = set(requested_ids)

    with h5py.File(source, "r") as file:
        group = _resolve_restart_group(file, restart_step)
        if "element_info" not in group:
            raise ValueError("重启动步缺少必要数据集：element_info")

        element_info = np.asarray(group["element_info"][...], dtype=np.int64)
        datasets = {
            name: np.ravel(group[name][...])
            for name in ("stress", "strain", "constitutive_variables")
            if name in group
        }
        offsets = _validate_restart_arrays(element_info, datasets)
        stress = datasets.get("stress")
        strain = datasets.get("strain")
        state = datasets.get("constitutive_variables")
        step_name = group.name.rsplit("/", 1)[-1]

        element_positions: dict[int, int] = {}
        for index, row in enumerate(element_info):
            element_id = int(row[0])
            if element_id in requested_set and element_id not in element_positions:
                element_positions[element_id] = index
        missing_ids = [element_id for element_id in requested_ids if element_id not in element_positions]
        if missing_ids:
            preview = ", ".join(str(value) for value in missing_ids[:20])
            suffix = " ..." if len(missing_ids) > 20 else ""
            raise ValueError(f"以下单元号未在 element_info 中找到：{preview}{suffix}")

        records: list[dict[str, int | float | str]] = []
        summaries: list[dict[str, int]] = []
        max_stress = max_strain = max_state = 0
        for index, row in enumerate(element_info):
            element_id = int(row[0])
            if element_id not in requested_set:
                continue
            material_type = int(row[1])
            gauss_points = int(row[2])
            stress_components = int(row[3])
            strain_components = int(row[4])
            state_variables = int(row[5])
            if stress is not None:
                max_stress = max(max_stress, stress_components)
            if strain is not None:
                max_strain = max(max_strain, strain_components)
            if state is not None:
                max_state = max(max_state, state_variables)
            summaries.append(
                {
                    "element_id": element_id,
                    "element_order_index": index,
                    "material_type": material_type,
                    "gauss_points": gauss_points,
                    "stress_components": stress_components,
                    "strain_components": strain_components,
                    "state_variables": state_variables,
                }
            )
            stress_start = int(offsets["stress"][index]) if stress is not None else 0
            strain_start = int(offsets["strain"][index]) if strain is not None else 0
            state_start = (
                int(offsets["constitutive_variables"][index]) if state is not None else 0
            )
            for gp_index in range(gauss_points):
                record: dict[str, int | float | str] = {
                    "restart_step": step_name,
                    "element_id": element_id,
                    "element_order_index": index,
                    "material_type": material_type,
                    "gauss_point": gp_index + 1,
                    "gauss_points": gauss_points,
                    "stress_components": stress_components,
                    "strain_components": strain_components,
                    "state_variables": state_variables,
                }
                if stress is not None:
                    for component in range(stress_components):
                        offset = stress_start + gp_index * stress_components + component
                        record[f"stress_{component + 1}"] = float(stress[offset])
                if strain is not None:
                    for component in range(strain_components):
                        offset = strain_start + gp_index * strain_components + component
                        record[f"strain_{component + 1}"] = float(strain[offset])
                if state is not None:
                    for component in range(state_variables):
                        offset = state_start + gp_index * state_variables + component
                        record[f"state_{component + 1}"] = float(state[offset])
                records.append(record)

    ordered_columns = [
        "restart_step",
        "element_id",
        "element_order_index",
        "material_type",
        "gauss_point",
        "gauss_points",
        "stress_components",
        "strain_components",
        "state_variables",
    ]
    ordered_columns.extend(f"stress_{index}" for index in range(1, max_stress + 1))
    ordered_columns.extend(f"strain_{index}" for index in range(1, max_strain + 1))
    ordered_columns.extend(f"state_{index}" for index in range(1, max_state + 1))
    data = pd.DataFrame(records).reindex(columns=ordered_columns)
    summary = pd.DataFrame(summaries)
    _write_restart_excel_atomic(data, summary, target)

    return OperationResult(
        "导出重启动单元高斯点数据",
        f"已导出 {len(summaries)} 个单元、{len(records)} 个高斯点的数据。",
        (target,),
        {"elements": len(summaries), "gauss_points": len(records)},
    )
