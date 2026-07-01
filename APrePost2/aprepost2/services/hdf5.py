from __future__ import annotations

import os
import tempfile
from pathlib import Path

import h5py

from aprepost2.services.common import OperationResult, checked_paths


def merge_hdf5(
    first_path: str, second_path: str, output_path: str, *, overwrite: bool = False
) -> OperationResult:
    if not output_path.lower().endswith((".h5", ".hdf5")):
        output_path += ".h5"
    first, target = checked_paths(first_path, output_path)
    second = Path(second_path).expanduser().resolve()
    if not second.is_file():
        raise FileNotFoundError(f"第二个 HDF5 文件不存在：{second}")
    if second == target:
        raise ValueError("第二个输入文件与输出文件不能相同")
    if target.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在：{target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    temporary_path: str | None = None
    replaced_frames = 0
    added_frames = 0
    try:
        descriptor, temporary_path = tempfile.mkstemp(
            dir=target.parent, prefix=f".{target.name}.", suffix=".tmp"
        )
        os.close(descriptor)
        with (
            h5py.File(first, "r") as source,
            h5py.File(second, "r") as addition,
            h5py.File(temporary_path, "w") as destination,
        ):
            for name in source:
                source.copy(name, destination)
            if "frames" in addition:
                frames = destination.require_group("frames")
                for frame_name in addition["frames"]:
                    if frame_name in frames:
                        del frames[frame_name]
                        replaced_frames += 1
                    addition["frames"].copy(frame_name, frames)
                    added_frames += 1
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)
    return OperationResult(
        "合并 HDF5",
        f"合并完成：从第二个文件复制 {added_frames} 个 frame，其中替换 {replaced_frames} 个。",
        (target,),
        {"copied_frames": added_frames, "replaced_frames": replaced_frames},
    )
