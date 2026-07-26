from __future__ import annotations

import os
import re
import shutil
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

from aprepost2.services.common import OperationResult


_ZONE_LINE = re.compile(r"^\s*ZONE\b", re.IGNORECASE)
_VARIABLES_START = re.compile(r"^\s*VARIABLES\s*=", re.IGNORECASE)
_HEADER_DIRECTIVE = re.compile(
    r"^\s*(?:TITLE|FILETYPE|DATASETAUXDATA|VARAUXDATA|GEOMETRY|TEXT)\b",
    re.IGNORECASE,
)
_QUOTED_VALUE = re.compile(r'"((?:\\.|[^"\\])*)"')
_SHARED_ZONE_DATA = re.compile(
    r"\b(?:VARSHARELIST|CONNECTIVITYSHAREZONE)\s*=", re.IGNORECASE
)
_STEP_FILE_STEM = re.compile(r"^(?P<name>.*?)[_-]?(?P<step>\d+)$")
_TECPLOT_BINARY_MAGIC = b"#!TDV"
_TECPLOT_ZONE_MARKER = 299.0
_TECPLOT_END_HEADER_MARKER = 357.0


@dataclass(frozen=True, slots=True)
class TecplotAsciiFile:
    path: Path
    preamble: str
    variables: tuple[str, ...]
    zones: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TecplotStepGroup:
    """Files belonging to one named output, ordered by numeric calculation step."""

    name: str
    steps: tuple[int, ...]
    paths: tuple[Path, ...]


@dataclass(frozen=True, slots=True)
class _TecplotBinaryFile:
    path: Path
    magic: bytes
    endian: str
    file_type: int
    variables: tuple[str, ...]
    header_records_offset: int
    end_header_offset: int


def discover_plt_files(
    directories: Iterable[str | Path], *, recursive: bool
) -> tuple[Path, ...]:
    """Return deterministic, de-duplicated Tecplot ASCII candidates."""
    found: list[Path] = []
    seen: set[str] = set()
    for value in directories:
        directory = Path(value).expanduser().resolve()
        if not directory.is_dir():
            raise NotADirectoryError(f"文件夹不存在：{directory}")
        candidates = directory.rglob("*") if recursive else directory.iterdir()
        for path in sorted(
            (item for item in candidates if item.is_file() and item.suffix.lower() == ".plt"),
            key=lambda item: str(item).casefold(),
        ):
            resolved = path.resolve()
            identity = os.path.normcase(str(resolved))
            if identity not in seen:
                seen.add(identity)
                found.append(resolved)
    return tuple(found)


def infer_tecplot_step(path: str | Path) -> tuple[str, int] | None:
    """Infer an editable output name and step from the file stem."""
    source = Path(path)
    match = _STEP_FILE_STEM.fullmatch(source.stem)
    if match is None:
        return None
    name = match.group("name").rstrip("_-").strip()
    return (name or source.stem), int(match.group("step"))


def group_tecplot_step_files(
    paths: Iterable[str | Path],
) -> tuple[TecplotStepGroup, ...]:
    """Group name_12.plt/name-12.plt files by name and numeric step."""
    grouped: dict[str, dict[int, Path]] = {}
    display_names: dict[str, str] = {}
    for value in paths:
        path = Path(value).expanduser().resolve()
        match = _STEP_FILE_STEM.fullmatch(path.stem)
        if match is None or path.suffix.lower() != ".plt":
            continue
        name = match.group("name").rstrip("_-").strip()
        if not name:
            continue
        step = int(match.group("step"))
        identity = name.casefold()
        by_step = grouped.setdefault(identity, {})
        if step in by_step:
            raise ValueError(
                f"输出 {name!r} 的计算步 {step} 重复：\n"
                f"{by_step[step]}\n{path}"
            )
        by_step[step] = path
        display_names.setdefault(identity, name)

    result: list[TecplotStepGroup] = []
    for identity in sorted(grouped):
        by_step = grouped[identity]
        if len(by_step) < 2:
            continue
        ordered = sorted(by_step.items())
        result.append(
            TecplotStepGroup(
                display_names[identity],
                tuple(step for step, _ in ordered),
                tuple(path for _, path in ordered),
            )
        )
    return tuple(result)


def group_tecplot_files_explicit(
    input_files: Sequence[str],
    output_names: Sequence[str],
    steps: Sequence[int],
) -> tuple[TecplotStepGroup, ...]:
    """Build editable groups without relying on file-name conventions."""
    if not (len(input_files) == len(output_names) == len(steps)):
        raise ValueError("\u6587\u4ef6\u3001\u8f93\u51fa\u540d\u4e0e\u8ba1\u7b97\u6b65\u6570\u91cf\u4e0d\u4e00\u81f4")
    if not input_files:
        raise ValueError("\u81f3\u5c11\u9700\u8981\u4e24\u4e2a PLT \u6587\u4ef6")

    grouped: dict[str, tuple[str, dict[int, Path]]] = {}
    seen_paths: set[str] = set()
    for file_value, name_value, step_value in zip(input_files, output_names, steps):
        path = Path(file_value).expanduser().resolve()
        if not path.is_file() or path.suffix.lower() != ".plt":
            raise FileNotFoundError(f"PLT \u6587\u4ef6\u4e0d\u5b58\u5728\uff1a{path}")
        path_identity = os.path.normcase(str(path))
        if path_identity in seen_paths:
            raise ValueError(f"\u8f93\u5165\u5217\u8868\u5305\u542b\u91cd\u590d\u6587\u4ef6\uff1a{path}")
        seen_paths.add(path_identity)

        name = str(name_value).strip()
        if not name:
            raise ValueError("\u5206\u7ec4\u8f93\u51fa\u540d\u4e0d\u80fd\u4e3a\u7a7a")
        try:
            step = int(step_value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"\u8ba1\u7b97\u6b65\u5fc5\u987b\u4e3a\u6574\u6570\uff1a{step_value}") from error
        if step < 0:
            raise ValueError(f"\u8ba1\u7b97\u6b65\u4e0d\u80fd\u4e3a\u8d1f\u6570\uff1a{step}")

        identity = name.casefold()
        display_name, by_step = grouped.setdefault(identity, (name, {}))
        if step in by_step:
            raise ValueError(
                f"\u8f93\u51fa {display_name!r} \u7684\u8ba1\u7b97\u6b65 {step} \u91cd\u590d\uff1a\n"
                f"{by_step[step]}\n{path}"
            )
        by_step[step] = path

    result: list[TecplotStepGroup] = []
    for identity in sorted(grouped):
        name, by_step = grouped[identity]
        if len(by_step) < 2:
            raise ValueError(f"\u8f93\u51fa {name!r} \u81f3\u5c11\u9700\u8981\u4e24\u4e2a\u8ba1\u7b97\u6b65")
        ordered = sorted(by_step.items())
        result.append(
            TecplotStepGroup(
                name,
                tuple(step for step, _ in ordered),
                tuple(path for _, path in ordered),
            )
        )
    return tuple(result)


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            pass
    # Tecplot ASCII is commonly pure ASCII. latin-1 provides a lossless final
    # fallback for legacy comments while structural tokens remain inspectable.
    return raw.decode("latin-1")


def _parse_variables(preamble: str, path: Path) -> tuple[str, ...]:
    lines = preamble.splitlines()
    start = next(
        (index for index, line in enumerate(lines) if _VARIABLES_START.match(line)),
        None,
    )
    if start is None:
        raise ValueError(f"未找到 VARIABLES 声明，不能确认变量体系：{path}")

    declaration: list[str] = []
    for index in range(start, len(lines)):
        line = lines[index]
        if index > start and _HEADER_DIRECTIVE.match(line):
            break
        declaration.append(line)
    text = "\n".join(declaration)
    text = _VARIABLES_START.sub("", text, count=1)
    quoted = _QUOTED_VALUE.findall(text)
    if quoted:
        variables = tuple(
            value.replace(r'\"', '"').replace(r"\\", "\\").strip()
            for value in quoted
        )
    else:
        variables = tuple(item for item in re.split(r"[,\s]+", text.strip()) if item)
    if not variables or any(not item for item in variables):
        raise ValueError(f"VARIABLES 声明为空或无法解析：{path}")
    return variables


def parse_tecplot_ascii(path: str | Path) -> TecplotAsciiFile:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"输入 PLT 文件不存在：{source}")
    text = _read_text(source)
    lines = text.splitlines(keepends=True)
    zone_indices = [index for index, line in enumerate(lines) if _ZONE_LINE.match(line)]
    if not zone_indices:
        raise ValueError(f"未找到 Tecplot ASCII ZONE：{source}")
    preamble = "".join(lines[: zone_indices[0]])
    zones = tuple(
        "".join(lines[start:end])
        for start, end in zip(zone_indices, zone_indices[1:] + [len(lines)])
    )
    return TecplotAsciiFile(source, preamble, _parse_variables(preamble, source), zones)


def _normalized_variables(variables: Sequence[str]) -> tuple[str, ...]:
    return tuple(re.sub(r"\s+", " ", item.strip()).casefold() for item in variables)


def _rename_zone(zone: str, case_name: str) -> str:
    escaped_name = case_name.replace("\\", "\\\\").replace('"', r'\"')
    title = f'T="{escaped_name}"'
    title_pattern = re.compile(r'\bT\s*=\s*"(?:\\.|[^"\\])*"', re.IGNORECASE)
    if title_pattern.search(zone):
        return title_pattern.sub(title, zone, count=1)
    return re.sub(r"^(\s*ZONE\b)", rf"\1 {title},", zone, count=1, flags=re.IGNORECASE)


def merge_tecplot_single_step(
    input_files: Sequence[str],
    case_names: Sequence[str],
    step: int,
    output_path: str,
    *,
    overwrite: bool = False,
) -> OperationResult:
    """Extract the 1-based Zone ordinal from each file and merge in given order."""
    if step < 1:
        raise ValueError("计算步必须从 1 开始")
    if not input_files:
        raise ValueError("至少需要添加一个 Tecplot ASCII .plt 文件")
    if len(input_files) != len(case_names):
        raise ValueError("输入文件数量与工况名称数量不一致")

    cleaned_names = [str(name).strip() for name in case_names]
    if any(not name for name in cleaned_names):
        raise ValueError("工况名称不能为空")
    duplicate_names = sorted(
        {name for name in cleaned_names if cleaned_names.count(name) > 1}
    )
    if duplicate_names:
        raise ValueError(f"工况名称不能重复：{', '.join(duplicate_names)}")

    sources = [Path(value).expanduser().resolve() for value in input_files]
    target = Path(output_path).expanduser().resolve()
    source_identities = {os.path.normcase(str(path)) for path in sources}
    if os.path.normcase(str(target)) in source_identities:
        raise ValueError("输出文件不能与任何输入文件相同，以免修改原始数据")
    if target.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在：{target}")
    target.parent.mkdir(parents=True, exist_ok=True)

    parsed = [parse_tecplot_ascii(path) for path in sources]
    reference_variables = _normalized_variables(parsed[0].variables)
    selected_zones: list[str] = []
    for item in parsed:
        if len(item.zones) < step:
            raise ValueError(
                f"指定计算步 {step} 不存在：{item.path}（仅有 {len(item.zones)} 个 Zone）"
            )
        if _normalized_variables(item.variables) != reference_variables:
            raise ValueError(
                "变量体系不兼容：\n"
                f"基准文件 {parsed[0].path.name}: {parsed[0].variables}\n"
                f"当前文件 {item.path.name}: {item.variables}"
            )
        zone = item.zones[step - 1]
        if _SHARED_ZONE_DATA.search(zone):
            raise ValueError(
                f"指定步包含跨 Zone 共享数据，不能独立提取：{item.path}。"
                "请先在 Tecplot 中导出为包含完整数据的 ASCII Zone。"
            )
        selected_zones.append(zone)

    parts = [parsed[0].preamble]
    if parts[0] and not parts[0].endswith(("\n", "\r")):
        parts[0] += "\n"
    for zone, case_name in zip(selected_zones, cleaned_names):
        renamed = _rename_zone(zone, case_name)
        parts.append(renamed)
        if not renamed.endswith(("\n", "\r")):
            parts.append("\n")
    output_text = "".join(parts)

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write(output_text)
            temporary_path = Path(stream.name)
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()

    return OperationResult(
        title="PLT 单步提取与合并完成",
        message=f"已按设定顺序合并 {len(parsed)} 个工况的第 {step} 个 Zone。",
        output_paths=(target,),
        metrics={
            "file_count": len(parsed),
            "step": step,
            "variable_count": len(parsed[0].variables),
        },
        log_lines=(
            f"变量数：{len(parsed[0].variables)}",
            "工况顺序：" + " → ".join(cleaned_names),
            "原始 PLT 文件均保持不变。",
        ),
    )



def _is_tecplot_binary(path: Path) -> bool:
    with path.open("rb") as stream:
        return stream.read(5) == _TECPLOT_BINARY_MAGIC


def _read_binary_int(stream, endian: str, field_name: str) -> int:
    raw = stream.read(4)
    if len(raw) != 4:
        raise ValueError(f"Tecplot binary 文件在读取 {field_name} 时意外结束")
    return struct.unpack(f"{endian}i", raw)[0]


def _read_binary_string(stream, endian: str, field_name: str) -> str:
    characters: list[str] = []
    for _ in range(1_000_000):
        value = _read_binary_int(stream, endian, field_name)
        if value == 0:
            return "".join(characters)
        if value < 0 or value > 0x10FFFF:
            raise ValueError(f"Tecplot binary 的 {field_name} 含无效字符码：{value}")
        characters.append(chr(value))
    raise ValueError(f"Tecplot binary 的 {field_name} 长度异常")


def _inspect_tecplot_binary(path: Path) -> _TecplotBinaryFile:
    with path.open("rb") as stream:
        magic = stream.read(8)
        if len(magic) != 8 or not magic.startswith(_TECPLOT_BINARY_MAGIC):
            raise ValueError(f"不是可识别的 Tecplot binary 文件：{path}")
        byte_order = stream.read(4)
        if byte_order == b"\x01\x00\x00\x00":
            endian = "<"
        elif byte_order == b"\x00\x00\x00\x01":
            endian = ">"
        else:
            raise ValueError(f"Tecplot binary 字节序标识无效：{path}")
        file_type = _read_binary_int(stream, endian, "文件类型")
        _read_binary_string(stream, endian, "数据集标题")
        variable_count = _read_binary_int(stream, endian, "变量数")
        if variable_count < 1 or variable_count > 1_000_000:
            raise ValueError(f"Tecplot binary 变量数异常：{path}（{variable_count}）")
        variables = tuple(
            _read_binary_string(stream, endian, f"变量 {index + 1}")
            for index in range(variable_count)
        )
        header_records_offset = stream.tell()
        marker = struct.pack(f"{endian}f", _TECPLOT_END_HEADER_MARKER)
        header_tail = stream.read(64 * 1024 * 1024)
        relative_offset = header_tail.find(marker)
        if relative_offset < 0:
            raise ValueError(f"未找到 Tecplot binary 文件头结束标识：{path}")
        end_header_offset = header_records_offset + relative_offset
        zone_marker = struct.pack(f"{endian}f", _TECPLOT_ZONE_MARKER)
        header_records = header_tail[:relative_offset]
        if not header_records.startswith(zone_marker):
            raise ValueError(f"Tecplot binary 首个 header record 不是 Zone：{path}")
        if header_records.count(zone_marker) != 1:
            raise ValueError(
                f"分步文件必须恰好包含一个 Zone：{path}。"
                "请先把每个计算步分别导出为单 Zone 文件。"
            )
    return _TecplotBinaryFile(
        path,
        magic,
        endian,
        file_type,
        variables,
        header_records_offset,
        end_header_offset,
    )


def _copy_binary_range(source: Path, target, start: int, end: int | None) -> None:
    with source.open("rb") as stream:
        stream.seek(start)
        remaining = None if end is None else end - start
        while remaining is None or remaining > 0:
            size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
            block = stream.read(size)
            if not block:
                break
            target.write(block)
            if remaining is not None:
                remaining -= len(block)
        if remaining not in (None, 0):
            raise ValueError(f"读取 Tecplot binary 数据不完整：{source}")


def _validate_binary_group(
    group: TecplotStepGroup,
) -> tuple[_TecplotBinaryFile, ...]:
    items = tuple(_inspect_tecplot_binary(path) for path in group.paths)
    reference = items[0]
    reference_variables = _normalized_variables(reference.variables)
    for item in items[1:]:
        if (
            item.magic != reference.magic
            or item.endian != reference.endian
            or item.file_type != reference.file_type
        ):
            raise ValueError(
                f"输出 {group.name!r} 的 Tecplot binary 版本、字节序或文件类型不一致："
                f"{reference.path.name} 与 {item.path.name}"
            )
        if _normalized_variables(item.variables) != reference_variables:
            raise ValueError(
                f"输出 {group.name!r} 的变量体系不兼容："
                f"{reference.path.name} 与 {item.path.name}"
            )
    return items


def _validate_ascii_group(
    group: TecplotStepGroup,
) -> tuple[TecplotAsciiFile, ...]:
    items = tuple(parse_tecplot_ascii(path) for path in group.paths)
    reference_variables = _normalized_variables(items[0].variables)
    for item in items:
        if len(item.zones) != 1:
            raise ValueError(
                f"分步文件必须恰好包含一个 Zone：{item.path}（当前 {len(item.zones)} 个）"
            )
        if _SHARED_ZONE_DATA.search(item.zones[0]):
            raise ValueError(f"单 Zone 分步文件不应包含跨 Zone 共享数据：{item.path}")
        if _normalized_variables(item.variables) != reference_variables:
            raise ValueError(
                f"输出 {group.name!r} 的变量体系不兼容："
                f"{items[0].path.name} 与 {item.path.name}"
            )
    return items


def _merge_binary_group(
    items: Sequence[_TecplotBinaryFile], target: Path
) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as output:
            temporary_path = Path(output.name)
            first = items[0]
            _copy_binary_range(first.path, output, 0, first.header_records_offset)
            for item in items:
                _copy_binary_range(
                    item.path,
                    output,
                    item.header_records_offset,
                    item.end_header_offset,
                )
            output.write(
                struct.pack(f"{first.endian}f", _TECPLOT_END_HEADER_MARKER)
            )
            for item in items:
                _copy_binary_range(item.path, output, item.end_header_offset + 4, None)
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _merge_ascii_group(items: Sequence[TecplotAsciiFile], target: Path) -> None:
    parts = [items[0].preamble]
    if parts[0] and not parts[0].endswith(("\n", "\r")):
        parts[0] += "\n"
    for item in items:
        parts.append(item.zones[0])
        if not item.zones[0].endswith(("\n", "\r")):
            parts.append("\n")

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            stream.write("".join(parts))
            temporary_path = Path(stream.name)
        os.replace(temporary_path, target)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def merge_tecplot_step_series(
    input_directory: str = "",
    output_directory: str = "",
    *,
    input_files: Sequence[str] | None = None,
    output_names: Sequence[str] | None = None,
    steps: Sequence[int] | None = None,
    recursive: bool = False,
    overwrite: bool = False,
) -> OperationResult:
    """Merge one-Zone PLT files using editable or file-name-derived groups."""
    if input_files is not None:
        if output_names is None or steps is None:
            raise ValueError("\u7f3a\u5c11\u53ef\u7f16\u8f91\u7684\u8f93\u51fa\u540d\u6216\u8ba1\u7b97\u6b65")
        groups = group_tecplot_files_explicit(input_files, output_names, steps)
        default_output_directory = groups[0].paths[0].parent
    else:
        if not str(input_directory).strip():
            raise ValueError("\u8bf7\u9009\u62e9 PLT \u6587\u4ef6\u5939")
        source_directory = Path(input_directory).expanduser().resolve()
        paths = discover_plt_files((source_directory,), recursive=recursive)
        groups = group_tecplot_step_files(paths)
        default_output_directory = source_directory
        if not groups:
            raise ValueError(
                "\u672a\u627e\u5230\u53ef\u5408\u5e76\u7684\u5206\u6b65\u6587\u4ef6\u3002"
                "\u8bf7\u68c0\u67e5\u6587\u4ef6\u540d\u6b65\u53f7\uff0c\u6216\u5728\u8868\u683c\u4e2d\u624b\u5de5\u7f16\u8f91\u3002"
            )
    target_directory = (
        Path(output_directory).expanduser().resolve()
        if str(output_directory).strip()
        else default_output_directory
    )

    plans: list[tuple[TecplotStepGroup, Path, str, tuple]] = []
    excluded_format_files: list[tuple[str, str, Path]] = []
    source_identities = {os.path.normcase(str(path)) for group in groups for path in group.paths}
    for group in groups:
        target = (target_directory / f"{group.name}_merged.plt").resolve()
        if os.path.normcase(str(target)) in source_identities:
            raise ValueError(f"输出文件不能与输入文件相同：{target}")
        if target.exists() and not overwrite:
            raise FileExistsError(f"输出文件已存在：{target}")
        binary_flags = tuple(_is_tecplot_binary(path) for path in group.paths)
        if any(binary_flags) and not all(binary_flags):
            binary_paths = [
                path for path, is_binary in zip(group.paths, binary_flags) if is_binary
            ]
            ascii_paths = [
                path
                for path, is_binary in zip(group.paths, binary_flags)
                if not is_binary
            ]
            if len(ascii_paths) == len(binary_paths):
                raise ValueError(
                    f"输出 {group.name!r} 中 ASCII 与 binary PLT 数量相同，"
                    "无法安全判断应保留哪一种格式。\n\n"
                    f"ASCII 文件（{len(ascii_paths)} 个）：\n"
                    + "\n".join(str(path) for path in ascii_paths)
                    + f"\n\nbinary 文件（{len(binary_paths)} 个）：\n"
                    + "\n".join(str(path) for path in binary_paths)
                )

            keep_binary = len(binary_paths) > len(ascii_paths)
            kept = [
                (step, path, is_binary)
                for step, path, is_binary in zip(
                    group.steps, group.paths, binary_flags
                )
                if is_binary == keep_binary
            ]
            excluded_paths = ascii_paths if keep_binary else binary_paths
            excluded_format = "ASCII" if keep_binary else "binary"
            kept_format = "binary" if keep_binary else "ASCII"
            excluded_format_files.extend(
                (group.name, excluded_format, path) for path in excluded_paths
            )
            group = TecplotStepGroup(
                group.name,
                tuple(step for step, _, _ in kept),
                tuple(path for _, path, _ in kept),
            )
            binary_flags = tuple(is_binary for _, _, is_binary in kept)
            if len(group.paths) < 2:
                raise ValueError(
                    f"输出 {group.name!r} 排除 {excluded_format} 文件后，"
                    f"仅剩 {len(group.paths)} 个 {kept_format} 文件，不能合并。"
                )
        if all(binary_flags):
            plans.append((group, target, "binary", _validate_binary_group(group)))
        else:
            plans.append((group, target, "ascii", _validate_ascii_group(group)))

    target_directory.mkdir(parents=True, exist_ok=True)
    output_paths: list[Path] = []
    log_lines: list[str] = []
    total_files = 0
    for group, target, file_format, items in plans:
        if file_format == "binary":
            _merge_binary_group(items, target)
        else:
            _merge_ascii_group(items, target)
        output_paths.append(target)
        total_files += len(group.paths)
        log_lines.append(
            f"{group.name}: 步号 {', '.join(map(str, group.steps))} -> {target.name}"
        )

    if excluded_format_files:
        log_lines.append(
            f"因组内格式不一致，已从本次合并排除 {len(excluded_format_files)} 个文件："
        )
        log_lines.extend(
            f"{group_name} | {file_format} | {path}"
            for group_name, file_format, path in excluded_format_files
        )

    return OperationResult(
        title="PLT 分步文件批量合并完成",
        message=(
            f"已将 {total_files} 个分步文件按计算步数值顺序合并为 "
            f"{len(output_paths)} 个 PLT 文件；"
            f"排除 {len(excluded_format_files)} 个格式不一致的文件。"
        ),
        output_paths=tuple(output_paths),
        metrics={
            "group_count": len(groups),
            "file_count": total_files,
            "excluded_format_file_count": len(excluded_format_files),
        },
        log_lines=tuple(log_lines) + ("原始 PLT 文件均保持不变。",),
    )
