from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class OperationResult:
    title: str
    message: str
    output_paths: tuple[Path, ...] = field(default_factory=tuple)
    metrics: dict[str, int | float | str] = field(default_factory=dict)
    log_lines: tuple[str, ...] = field(default_factory=tuple)


def checked_paths(input_path: str, output_path: str) -> tuple[Path, Path]:
    source = Path(input_path).expanduser().resolve()
    target = Path(output_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"输入文件不存在：{source}")
    if source == target:
        raise ValueError("输入文件与输出文件不能相同，以免覆盖原始数据")
    return source, target
