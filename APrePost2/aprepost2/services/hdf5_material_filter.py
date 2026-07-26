from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import h5py
import numpy as np

from aprepost2.services.common import OperationResult, checked_paths


REQUIRED_DATASETS = (
    "element_info",
    "stress",
    "strain",
    "constitutive_variables",
)
SUPPORTED_ROOTS = ("output_for_initial_condition", "output_for_restart")


def _parse_element_ids_file(value: str) -> list[int]:
    source = Path(value).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"单元号文件不存在：{source}")
    text = source.read_text(encoding="utf-8-sig")

    lines = []
    for line in text.splitlines():
        lines.append(line.split("#", 1)[0].split("//", 1)[0])
    element_ids = [
        int(token) for token in re.findall(r"[-+]?\d+", "\n".join(lines))
    ]
    if len(element_ids) >= 2 and element_ids[0] == len(element_ids) - 1:
        element_ids = element_ids[1:]
    if not element_ids:
        raise ValueError("单元号文件中未读取到单元号")
    return list(dict.fromkeys(element_ids))


def _candidate_group_paths(file: h5py.File) -> list[str]:
    candidates: list[str] = []
    for root_name in SUPPORTED_ROOTS:
        root = file.get(root_name)
        if not isinstance(root, h5py.Group):
            continue
        for child_name, child in root.items():
            if isinstance(child, h5py.Group) and all(
                name in child for name in REQUIRED_DATASETS
            ):
                candidates.append(f"{root_name}/{child_name}")
    return candidates


def _resolve_data_group(file: h5py.File, group_path: str) -> h5py.Group:
    requested = group_path.strip().strip("/")
    if not requested or requested.lower() == "auto":
        candidates = _candidate_group_paths(file)
        if len(candidates) != 1:
            available = ", ".join(candidates) if candidates else "无"
            raise ValueError(
                "数据组路径设为 auto 时，文件中必须恰好有一个初始/重启动数据组；"
                f"当前候选：{available}"
            )
        requested = candidates[0]

    group = file.get(requested)
    if not isinstance(group, h5py.Group):
        raise ValueError(f"HDF5 中不存在数据组：/{requested}")
    missing = [name for name in REQUIRED_DATASETS if name not in group]
    if missing:
        raise ValueError(f"数据组 /{requested} 缺少必要数据集：{', '.join(missing)}")
    return group


def _validate_element_arrays(
    element_info: np.ndarray,
    stress: np.ndarray,
    strain: np.ndarray,
    state: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if element_info.ndim != 2 or element_info.shape[1] != 6:
        raise ValueError(
            "element_info 必须是 N x 6 数组：单元号、单元材料类型、高斯点数、"
            "应力分量数、应变分量数、内变量个数"
        )
    for name, values in (
        ("stress", stress),
        ("strain", strain),
        ("constitutive_variables", state),
    ):
        if values.ndim != 1:
            raise ValueError(f"{name} 必须是一维扁平数组，当前形状为 {values.shape}")

    counts = element_info[:, 2:6].astype(np.int64, copy=False)
    if np.any(counts < 0):
        raise ValueError("element_info 中高斯点数或分量个数不能为负")
    stress_counts = counts[:, 0] * counts[:, 1]
    strain_counts = counts[:, 0] * counts[:, 2]
    state_counts = counts[:, 0] * counts[:, 3]
    expected = (
        int(np.sum(stress_counts)),
        int(np.sum(strain_counts)),
        int(np.sum(state_counts)),
    )
    actual = (int(stress.size), int(strain.size), int(state.size))
    if actual != expected:
        raise ValueError(
            "高斯点数组长度与 element_info 不一致："
            f"stress {actual[0]}/{expected[0]}，"
            f"strain {actual[1]}/{expected[1]}，"
            f"constitutive_variables {actual[2]}/{expected[2]}"
        )
    return (
        np.concatenate(([0], np.cumsum(stress_counts))),
        np.concatenate(([0], np.cumsum(strain_counts))),
        np.concatenate(([0], np.cumsum(state_counts))),
    )


def _filter_flat_array(
    values: np.ndarray, offsets: np.ndarray, keep_elements: np.ndarray
) -> np.ndarray:
    entry_counts = np.diff(offsets)
    return values[np.repeat(keep_elements, entry_counts)]


def _replace_dataset(group: h5py.Group, name: str, values: np.ndarray) -> None:
    original = group[name]
    attributes = dict(original.attrs)
    dtype = original.dtype
    creation: dict[str, object] = {}
    if original.compression is not None:
        creation["compression"] = original.compression
        creation["compression_opts"] = original.compression_opts
    if original.shuffle:
        creation["shuffle"] = True
    if original.fletcher32:
        creation["fletcher32"] = True
    if original.scaleoffset is not None:
        creation["scaleoffset"] = original.scaleoffset

    del group[name]
    replacement = group.create_dataset(name, data=values, dtype=dtype, **creation)
    for key, value in attributes.items():
        replacement.attrs[key] = value


def delete_hdf5_data_by_element_ids(
    input_path: str,
    group_path: str,
    element_ids_path: str,
    output_path: str,
    *,
    overwrite: bool = False,
) -> OperationResult:
    """Copy an initial/restart HDF5 file while removing selected elements."""
    if not output_path.lower().endswith((".h5", ".hdf5")):
        output_path += ".h5"
    source, target = checked_paths(input_path, output_path)
    if target.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在：{target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    requested_ids = _parse_element_ids_file(element_ids_path)
    requested_set = set(requested_ids)
    temporary_path: str | None = None
    try:
        descriptor, temporary_path = tempfile.mkstemp(
            dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
        )
        os.close(descriptor)
        with (
            h5py.File(source, "r") as source_file,
            h5py.File(temporary_path, "w") as destination,
        ):
            source_group = _resolve_data_group(source_file, group_path)
            resolved_group_path = source_group.name.strip("/")
            for key, value in source_file.attrs.items():
                destination.attrs[key] = value
            for name in source_file:
                source_file.copy(name, destination)

            group = destination[resolved_group_path]
            element_info_dataset = group["element_info"]
            element_info = np.asarray(element_info_dataset[...])
            stress = np.asarray(group["stress"][...])
            strain = np.asarray(group["strain"][...])
            state = np.asarray(group["constitutive_variables"][...])
            stress_offsets, strain_offsets, state_offsets = _validate_element_arrays(
                element_info, stress, strain, state
            )

            available_element_ids = set(
                element_info[:, 0].astype(np.int64, copy=False).tolist()
            )
            missing = [
                element_id
                for element_id in requested_ids
                if element_id not in available_element_ids
            ]
            if missing:
                raise ValueError(
                    "以下单元号未在 element_info 中找到："
                    + ", ".join(str(value) for value in missing)
                )

            keep_elements = ~np.isin(element_info[:, 0], requested_ids)
            deleted_elements = int(np.count_nonzero(~keep_elements))
            remaining_elements = int(np.count_nonzero(keep_elements))
            if remaining_elements == 0:
                raise ValueError("筛除后无剩余单元；为避免生成无效文件，已取消操作")

            deleted_gauss_points = int(
                np.sum(element_info[~keep_elements, 2], dtype=np.int64)
            )
            filtered_info = element_info[keep_elements]
            filtered_stress = _filter_flat_array(
                stress, stress_offsets, keep_elements
            )
            filtered_strain = _filter_flat_array(
                strain, strain_offsets, keep_elements
            )
            filtered_state = _filter_flat_array(state, state_offsets, keep_elements)

            _replace_dataset(group, "element_info", filtered_info)
            _replace_dataset(group, "stress", filtered_stress)
            _replace_dataset(group, "strain", filtered_strain)
            _replace_dataset(group, "constitutive_variables", filtered_state)
            _validate_element_arrays(
                np.asarray(group["element_info"][...]),
                np.asarray(group["stress"][...]),
                np.asarray(group["strain"][...]),
                np.asarray(group["constitutive_variables"][...]),
            )

        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)

    return OperationResult(
        "按单元号删除初始/重启动数据",
        f"已从 /{resolved_group_path} 删除 {deleted_elements} 个指定单元、"
        f"{deleted_gauss_points} 个高斯点；"
        f"保留 {remaining_elements} 个单元。",
        (target,),
        {
            "deleted_elements": deleted_elements,
            "deleted_gauss_points": deleted_gauss_points,
            "remaining_elements": remaining_elements,
            "group_path": resolved_group_path,
        },
    )
