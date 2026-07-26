from __future__ import annotations

import datetime as dt
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from aprepost2.services.common import OperationResult


def _cell(frame: pd.DataFrame, row: int, column: int, default=None, cast=None):
    if row >= frame.shape[0] or column >= frame.shape[1]:
        return default
    value = frame.iat[row, column]
    if pd.isna(value):
        return default
    if cast is None:
        return value
    try:
        return cast(value)
    except (TypeError, ValueError):
        return default


def _time_number(value) -> float:
    if isinstance(value, pd.Timestamp):
        return value.timestamp()
    if isinstance(value, (dt.datetime, dt.date)):
        return pd.Timestamp(value).timestamp()
    return float(value)


def _time_array(values) -> np.ndarray:
    return np.asarray([_time_number(value) for value in values], dtype=np.float64)


def _identity_key(value) -> str:
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value).strip()


def _measurement_label(frame: pd.DataFrame):
    """兼容旧测值工作簿中两种 Label 布局。"""
    if frame.empty:
        return None
    first_row = frame.iloc[0]
    for column, value in enumerate(first_row):
        if str(value).strip().lower() != "label":
            continue
        for candidate in first_row.iloc[column + 1 :]:
            if not pd.isna(candidate) and str(candidate).strip():
                return candidate
    # 最早一批模板没有写“Label”标题，而是直接把标签放在 E1。
    return _cell(frame, 0, 4)


def _resolve_sheet_name(sheets: dict[str, pd.DataFrame], requested: object) -> str | None:
    """Excel 工作表名按 Excel 自身规则做大小写不敏感匹配。"""
    text = str(requested).strip()
    if text in sheets:
        return text
    normalized = text.casefold()
    return next(
        (name for name in sheets if str(name).strip().casefold() == normalized), None
    )


def _interpolate(
    times,
    values,
    targets,
    *,
    outside_value: float = 0.0,
) -> np.ndarray:
    source_time = _time_array(times)
    source_values = np.asarray(values, dtype=np.float64)
    target_time = _time_array(targets)
    valid = np.isfinite(source_time) & np.isfinite(source_values)
    if np.count_nonzero(valid) < 2:
        return np.full(len(target_time), outside_value, dtype=np.float64)
    order = np.argsort(source_time[valid])
    x = source_time[valid][order]
    y = source_values[valid][order]
    unique_x, unique_indices = np.unique(x, return_index=True)
    y = y[unique_indices]
    result = np.interp(target_time, unique_x, y)
    result[(target_time < unique_x[0]) | (target_time > unique_x[-1])] = outside_value
    return result


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    name: str
    method: int
    direction: int
    calculation_scale: float
    measurement_scale: float
    calculation_output_scale: float
    coordinate_axis: int
    cad_x_axis: int
    cad_y_axis: int
    cad_x_note_offset: float
    cad_y_note_offset: float
    text_size: float
    real_initial_value: float | None
    calculation_initial_value: float | None
    read_method: int
    forced_initial_time: object | None
    end_times: np.ndarray
    step_to_time: dict[float, object]
    calculation_book: Path
    working_condition: str
    resort_groups: tuple[tuple[float, ...], ...] = ()


@dataclass(frozen=True, slots=True)
class PointMapping:
    label: object
    point_id: object
    result_id: int
    coordinates: np.ndarray
    result_type: str


@dataclass(slots=True)
class MonitorPoint:
    mapping: PointMapping
    group_name: str
    initial_time: object
    measured_time: np.ndarray = field(default_factory=lambda: np.empty(0))
    measured_values: np.ndarray = field(default_factory=lambda: np.empty(0))
    calculated_steps: np.ndarray = field(default_factory=lambda: np.empty(0))
    calculated_values: np.ndarray = field(default_factory=lambda: np.empty((0, 0)))


def _scenario_from_workbook(
    sheets: dict[str, pd.DataFrame], control: pd.DataFrame, row: int, root: Path
) -> ScenarioConfig:
    name = str(_cell(control, row, 0, ""))
    if not name or name not in sheets:
        raise ValueError(f"control 工作表第 {row + 1} 行引用的配置表不存在：{name}")
    frame = sheets[name]
    offset = 2
    end_count = int(_cell(frame, 1, 3, 0, int) or 0)
    end_times = frame.iloc[2 : 2 + end_count, 3].dropna().to_numpy()
    step_count = int(_cell(frame, 0, 4, 0, int) or 0)
    step_times = frame.iloc[1 : 1 + step_count, 5].dropna().to_numpy()
    steps = frame.iloc[1 : 1 + step_count, 6].dropna().to_numpy()
    pair_count = min(len(step_times), len(steps))
    calculation_name = str(_cell(frame, 4 + offset, 0, ""))
    calculation_book = Path(calculation_name)
    if not calculation_book.is_absolute():
        calculation_book = root / calculation_book

    resort_groups: list[tuple[float, ...]] = []
    if int(_cell(frame, 0, 9, 0, int) or 0) == 1:
        group_count = int(_cell(frame, 1, 9, 0, int) or 0)
        for group_index in range(group_count):
            item_count = int(_cell(frame, group_index + 2, 8, 0, int) or 0)
            values = frame.iloc[group_index + 2, 9 : 9 + item_count].dropna()
            resort_groups.append(tuple(float(value) for value in values))

    initial_time = _cell(frame, 15 + offset, 1, None)
    if initial_time == 0:
        initial_time = None
    real_initial = float(_cell(frame, 8 + offset, 1, -1, float))
    calc_initial = float(_cell(frame, 10 + offset, 1, -1, float))
    return ScenarioConfig(
        name=name,
        method=int(_cell(frame, 0 + offset, 1, 1, int)),
        direction=int(_cell(frame, 1 + offset, 1, 0, int)),
        calculation_scale=float(_cell(frame, 2 + offset, 1, 1.0, float)),
        measurement_scale=float(_cell(frame, 3 + offset, 1, 1.0, float)),
        calculation_output_scale=float(_cell(frame, 9 + offset, 1, -1000.0, float)),
        cad_x_axis=int(_cell(frame, 5 + offset, 1, 0, int)),
        cad_y_axis=int(_cell(frame, 6 + offset, 1, 1, int)),
        coordinate_axis=int(_cell(frame, 7 + offset, 1, 1, int)),
        real_initial_value=None if real_initial == -1 else real_initial,
        calculation_initial_value=None if calc_initial == -1 else calc_initial,
        cad_x_note_offset=float(_cell(frame, 11 + offset, 1, 0.0, float)),
        cad_y_note_offset=float(_cell(frame, 12 + offset, 1, -3.0, float)),
        text_size=float(_cell(frame, 13 + offset, 1, 4.0, float)),
        read_method=int(_cell(frame, 14 + offset, 1, 1, int)),
        forced_initial_time=initial_time,
        end_times=end_times,
        step_to_time={
            float(steps[index]): step_times[index] for index in range(pair_count)
        },
        calculation_book=calculation_book,
        working_condition=str(_cell(frame, 0, 1, "")),
        resort_groups=tuple(resort_groups),
    )


def _point_mappings(control: pd.DataFrame) -> dict[tuple[str, str], PointMapping]:
    count = int(_cell(control, 0, 1, 0, int) or 0)
    mappings: dict[tuple[str, str], PointMapping] = {}
    for row in range(min(count, len(control))):
        label = _cell(control, row, 2)
        point_id = _cell(control, row, 3)
        result_id = int(_cell(control, row, 4, 0, int) or 0)
        # control 的 F:H 是三维坐标，I 列是 node/ele 类型。旧版只读取 F:H；
        # 这里不能把 I 列误当成第 4 个坐标分量。
        coordinates = np.asarray(
            [
                float(_cell(control, row, column, 0.0, float))
                for column in range(5, 8)
            ],
            dtype=np.float64,
        )
        result_type = str(_cell(control, row, 8, "node")).lower()
        if result_type not in {"node", "ele"}:
            result_type = "node"
        mapping = PointMapping(label, point_id, result_id, coordinates, result_type)
        mappings[(_identity_key(label), _identity_key(point_id))] = mapping
    return mappings


def _load_monitor_points(
    scenario: ScenarioConfig, mappings: dict[tuple[str, str], PointMapping]
) -> list[list[MonitorPoint]]:
    if not scenario.calculation_book.is_file():
        raise FileNotFoundError(f"反演测值工作簿不存在：{scenario.calculation_book}")
    raw = pd.read_excel(scenario.calculation_book, sheet_name=None, header=None)
    first = next(iter(raw.values()))
    group_count = int(_cell(first, 0, 1, 0, int) or 0)
    label = _measurement_label(first)
    if label is None or not str(label).strip():
        raise ValueError(
            f"测值工作簿 {scenario.calculation_book} 的首个工作表未找到测点标签；"
            "请检查首行是否包含“Label”及其右侧的标签值"
        )
    groups: list[list[MonitorPoint]] = []
    for group_index in range(group_count):
        requested_group_name = str(_cell(first, 3 * group_index + 1, 0, ""))
        group_name = _resolve_sheet_name(raw, requested_group_name)
        if group_name is None:
            raise ValueError(f"测值工作簿缺少工作表：{requested_group_name}")
        identifiers = first.iloc[3 * group_index + 2].dropna().to_numpy()
        initial_times = first.iloc[3 * group_index + 3].to_numpy()
        no_header = raw[group_name]
        data_rows = no_header.iloc[1:].reset_index(drop=True)
        filled = data_rows.infer_objects(copy=False).ffill().bfill()
        group: list[MonitorPoint] = []
        for point_index, point_id in enumerate(identifiers):
            mapping = mappings.get((_identity_key(label), _identity_key(point_id)))
            if mapping is None:
                raise ValueError(f"control 工作表未配置测点：label={label}, id={point_id}")
            initial_time = (
                scenario.forced_initial_time
                if scenario.forced_initial_time is not None
                else initial_times[point_index]
            )
            point = MonitorPoint(mapping, group_name, initial_time)
            if scenario.read_method == 1:
                point.measured_time = no_header.iloc[1:, 0].dropna().to_numpy()
                point.measured_values = (
                    filled.iloc[: len(point.measured_time), point_index + 1]
                    .astype(float)
                    .to_numpy()
                )
            else:
                point.measured_time = (
                    no_header.iloc[1:, point_index * 2].dropna().to_numpy()
                )
                point.measured_values = (
                    filled.iloc[: len(point.measured_time), point_index * 2 + 1]
                    .astype(float)
                    .to_numpy()
                )
            group.append(point)
        groups.append(group)
    return groups


def _find_result_file(result_id: int, result_type: str, roots: tuple[Path, ...]) -> Path:
    name = f"{result_id}.{result_type}"
    for root in roots:
        candidate = root / name
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"找不到计算时程文件：{name}")


def _load_calculated_values(
    points: list[list[MonitorPoint]], scenario: ScenarioConfig, roots: tuple[Path, ...]
) -> None:
    for group in points:
        for point in group:
            path = _find_result_file(
                point.mapping.result_id, point.mapping.result_type, roots
            )
            frame = pd.read_csv(path, sep=r"\s+", engine="python")
            if frame.shape[1] < 2:
                raise ValueError(f"计算时程文件至少需要 step 和一个结果列：{path}")
            point.calculated_steps = pd.to_numeric(
                frame.iloc[:, 0], errors="raise"
            ).to_numpy(dtype=float)
            point.calculated_values = frame.iloc[:, 1:].apply(
                pd.to_numeric, errors="coerce"
            ).to_numpy(dtype=float)


def _initial_value(times, values, initial_time, explicit: float | None):
    if explicit is not None:
        return explicit
    return _interpolate(times, values, [initial_time], outside_value=float(values[0]))[0]


def _cad_columns(
    point: MonitorPoint,
    values: np.ndarray,
    scenario: ScenarioConfig,
    *,
    measured: bool,
) -> tuple[list[str], list[str]]:
    coordinates: list[str] = []
    notes: list[str] = []
    scale = scenario.measurement_scale if measured else scenario.calculation_scale
    note_scale = 1.0 if measured else scenario.calculation_output_scale
    for value in values:
        location = point.mapping.coordinates.copy()
        location[scenario.coordinate_axis] += value * scale
        x = location[scenario.cad_x_axis]
        y = location[scenario.cad_y_axis]
        coordinates.append(f"{x},{y}")
        note_x = x + (scenario.cad_x_note_offset if measured else -scenario.cad_x_note_offset)
        note_y = y + (scenario.cad_y_note_offset if measured else -scenario.cad_y_note_offset)
        notes.append(
            f"-text j ml {note_x},{note_y} {scenario.text_size} 0 {int(value * note_scale)}"
        )
    return coordinates, notes


def _point_results(point: MonitorPoint, scenario: ScenarioConfig) -> dict[str, np.ndarray | list[str]]:
    measured_end = _interpolate(
        point.measured_time, point.measured_values, scenario.end_times
    )
    measured_initial = _initial_value(
        point.measured_time,
        point.measured_values,
        point.initial_time,
        scenario.real_initial_value,
    )
    measured_increment = measured_end - measured_initial

    available = [
        (step, scenario.step_to_time[float(step)], row)
        for step, row in zip(point.calculated_steps, point.calculated_values)
        if float(step) in scenario.step_to_time
    ]
    if available:
        calculated_time = [item[1] for item in available]
        calculated_values = np.asarray([item[2] for item in available])
        direction = scenario.direction
        if direction >= calculated_values.shape[1]:
            raise ValueError(
                f"时程文件 {point.mapping.result_id}.{point.mapping.result_type} "
                f"没有方向索引 {direction}"
            )
        selected = calculated_values[:, direction]
        calculated_end = _interpolate(calculated_time, selected, scenario.end_times)
        calculated_initial = (
            0.0
            if scenario.calculation_initial_value is not None
            else _initial_value(
                calculated_time, selected, point.initial_time, None
            )
        )
        calculated_increment = calculated_end - calculated_initial
    else:
        calculated_end = np.zeros(len(scenario.end_times))
        calculated_increment = np.zeros(len(scenario.end_times))

    real_end_cad, real_end_notes = _cad_columns(
        point, measured_end, scenario, measured=True
    )
    real_increment_cad, real_increment_notes = _cad_columns(
        point, measured_increment, scenario, measured=True
    )
    calc_end_cad, calc_end_notes = _cad_columns(
        point, calculated_end, scenario, measured=False
    )
    calc_increment_cad, calc_increment_notes = _cad_columns(
        point, calculated_increment, scenario, measured=False
    )
    return {
        "measured_end": measured_end,
        "measured_increment": measured_increment,
        "calculated_end": calculated_end * scenario.calculation_output_scale,
        "calculated_increment": calculated_increment
        * scenario.calculation_output_scale,
        "real_end_cad": real_end_cad,
        "real_increment_cad": real_increment_cad,
        "calc_end_cad": calc_end_cad,
        "calc_increment_cad": calc_increment_cad,
        "real_end_notes": real_end_notes,
        "real_increment_notes": real_increment_notes,
        "calc_end_notes": calc_end_notes,
        "calc_increment_notes": calc_increment_notes,
    }


def _safe_sheet(name: str) -> str:
    for character in ':\\/?*[]':
        name = name.replace(character, "_")
    return (name or "Sheet")[:31]


def _atomic_write_excel(path: Path, writer_function) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.stem}.", suffix=".xlsx"
    )
    os.close(descriptor)
    try:
        with pd.ExcelWriter(temporary, engine="openpyxl") as writer:
            writer_function(writer)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def _write_summary(
    path: Path,
    groups: list[list[MonitorPoint]],
    scenario: ScenarioConfig,
) -> None:
    result_map = {
        point.mapping.point_id: _point_results(point, scenario)
        for group in groups
        for point in group
    }
    ordered_groups = groups
    if scenario.resort_groups:
        lookup = {
            float(point.mapping.point_id): point for group in groups for point in group
        }
        ordered_groups = [
            [lookup[identifier] for identifier in identifiers if identifier in lookup]
            for identifiers in scenario.resort_groups
        ]

    def write(writer):
        for group_index, group in enumerate(ordered_groups):
            if not group:
                continue
            sheet_name = _safe_sheet(
                group[0].group_name if group_index < len(groups) else f"group_{group_index + 1}"
            )
            coordinate_frame = pd.DataFrame(
                {
                    f"{point.mapping.point_id}_coor": point.mapping.coordinates
                    for point in group
                }
            )
            coordinate_frame.to_excel(
                writer, sheet_name=sheet_name, startrow=0, startcol=1, index=False
            )
            block_names = (
                "measured_end",
                "measured_increment",
                "calculated_end",
                "calculated_increment",
            )
            cad_names = (
                "real_end_cad",
                "real_increment_cad",
                "calc_end_cad",
                "calc_increment_cad",
            )
            note_names = (
                "real_end_notes",
                "real_increment_notes",
                "calc_end_notes",
                "calc_increment_notes",
            )
            block_height = len(scenario.end_times) + 1
            for block_index, (block, cad, note) in enumerate(
                zip(block_names, cad_names, note_names)
            ):
                start_row = 4 + block_index * block_height
                pd.DataFrame({"time": scenario.end_times}).to_excel(
                    writer, sheet_name=sheet_name, startrow=start_row, index=False
                )
                pd.DataFrame(
                    {
                        str(point.mapping.point_id): result_map[point.mapping.point_id][block]
                        for point in group
                    }
                ).to_excel(
                    writer,
                    sheet_name=sheet_name,
                    startrow=start_row,
                    startcol=1,
                    index=False,
                )
                pd.DataFrame(
                    {
                        str(point.mapping.point_id): result_map[point.mapping.point_id][cad]
                        for point in group
                    }
                ).to_excel(
                    writer,
                    sheet_name=sheet_name,
                    startrow=start_row,
                    startcol=len(group) + 2,
                    index=False,
                )
                pd.DataFrame(
                    {
                        str(point.mapping.point_id): result_map[point.mapping.point_id][note]
                        for point in group
                    }
                ).to_excel(
                    writer,
                    sheet_name=sheet_name,
                    startrow=start_row,
                    startcol=2 * len(group) + 2,
                    index=False,
                )

    _atomic_write_excel(path, write)


def _write_full_series(
    path: Path, groups: list[list[MonitorPoint]], scenario: ScenarioConfig
) -> None:
    def write(writer):
        for group in groups:
            if not group:
                continue
            measured: dict[str, pd.Series] = {}
            calculated: dict[str, pd.Series] = {}
            for point in group:
                key = f"{point.mapping.label}{point.mapping.point_id}"
                measured[f"{key}_time"] = pd.Series(point.measured_time)
                measured[f"{key}_measured"] = pd.Series(point.measured_values)
                if len(point.calculated_values):
                    calculated[f"{key}_step"] = pd.Series(point.calculated_steps)
                    calculated[f"{key}_calculated"] = pd.Series(
                        point.calculated_values[:, scenario.direction]
                        * scenario.calculation_output_scale
                    )
            frame = pd.concat(
                [pd.DataFrame(measured), pd.DataFrame(calculated)], axis=1
            )
            frame.to_excel(
                writer, sheet_name=_safe_sheet(group[0].group_name), index=False
            )

    _atomic_write_excel(path, write)


def inversion_postprocess(
    control_path: str,
    file_count: int,
    dimension: int,
    output_directory: str = ".",
    *,
    overwrite: bool = False,
) -> OperationResult:
    source = Path(control_path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"反演控制工作簿不存在：{source}")
    if int(file_count) <= 0:
        raise ValueError("文件数量必须大于 0")
    if int(dimension) not in (2, 3):
        raise ValueError("维度只能为 2 或 3")
    sheets = pd.read_excel(source, sheet_name=None, header=None)
    if "control" not in sheets:
        raise ValueError("反演控制工作簿缺少 control 工作表")
    control = sheets["control"]
    mappings = _point_mappings(control)
    if not mappings:
        raise ValueError("control 工作表没有有效的测点映射")
    outputs: list[Path] = []
    log_lines: list[str] = [
        f"控制工作簿：{source}",
        f"已读取 {len(sheets)} 个工作表、{len(mappings)} 条测点映射。",
        f"请求处理工况数：{int(file_count)}；空间维度：{int(dimension)}D。",
    ]
    roots = (source.parent, Path.cwd())
    output_root = Path(output_directory).expanduser()
    if str(output_root) == ".":
        output_root = source.parent
    output_root = output_root.resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    log_lines.append(f"输出目录：{output_root}")
    for scenario_index in range(1, int(file_count) + 1):
        try:
            scenario = _scenario_from_workbook(
                sheets, control, scenario_index, source.parent
            )
            log_lines.append(
                f"[{scenario_index}/{int(file_count)}] 工况“{scenario.name}”："
                f"测值工作簿 {scenario.calculation_book.name}，"
                f"目标时刻 {len(scenario.end_times)} 个，步时映射 {len(scenario.step_to_time)} 条。"
            )
            groups = _load_monitor_points(scenario, mappings)
            point_count = sum(len(group) for group in groups)
            log_lines.append(
                f"[{scenario_index}/{int(file_count)}] 已读取 {len(groups)} 个测点组、"
                f"{point_count} 个测点；结果方向索引 {scenario.direction}。"
            )
            _load_calculated_values(groups, scenario, roots)
        except Exception as error:
            scenario_name = str(_cell(control, scenario_index, 0, "未知工况"))
            raise type(error)(
                f"第 {scenario_index}/{int(file_count)} 组工况“{scenario_name}”处理失败：{error}"
            ) from error
        base_name = scenario.calculation_book.name
        summary = output_root / f"out{base_name}"
        full_series = output_root / f"out2{base_name}"
        existing = [path for path in (summary, full_series) if path.exists()]
        if existing and not overwrite:
            raise FileExistsError(
                "以下输出已存在，请更换输出目录或明确允许覆盖："
                + "，".join(str(path) for path in existing)
            )
        _write_summary(summary, groups, scenario)
        _write_full_series(full_series, groups, scenario)
        outputs.extend((summary, full_series))
        log_lines.append(
            f"[{scenario_index}/{int(file_count)}] 完成：生成 {summary.name}、{full_series.name}。"
        )
    return OperationResult(
        "反演后处理",
        f"反演后处理完成：处理 {file_count} 组配置，生成 {len(outputs)} 个工作簿。",
        tuple(outputs),
        {"scenarios": int(file_count), "workbooks": len(outputs)},
        tuple(log_lines),
    )
