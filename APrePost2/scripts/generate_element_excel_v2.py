"""生成当前 APrePost2 单元类型列表。

清单以 ``ELEMENT_TYPE_REGISTRY`` 为准，避免文档与实际可解析类型脱节。
"""
from __future__ import annotations

import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from aprepost2.domain.elements.registry import ELEMENT_TYPE_REGISTRY  # noqa: E402
from aprepost2.domain.elements.response import (  # noqa: E402
    ELEMENT_RESPONSE_TYPE_BY_T_ID,
    ElementResponseType,
)

DOCS_DIR = PROJECT_ROOT / "docs"
OUTPUTS = (
    DOCS_DIR / "element_types_v2.xlsx",
    DOCS_DIR / "单元类型对比表.xlsx",
)

HEADER_FONT = Font(name="微软雅黑", bold=True, size=10, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
NOTE_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
NEW_FILL = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style="thin"),
    right=Side(style="thin"),
    top=Side(style="thin"),
    bottom=Side(style="thin"),
)
WRAP_TOP = Alignment(wrap_text=True, vertical="top")


CLASS_DETAIL = {
    "QuadSolid2D": {
        "category": "二维实体",
        "nodes": "4 固定",
        "payload": "A",
        "structure": "4 节点四边形；无前言；按输入顺序保存真实节点编号。",
        "faces": "无",
        "note": "102 已从四节点四边形中移出，归入 QuadraticQuad2D。",
    },
    "QuadraticQuad2D": {
        "category": "二维实体",
        "nodes": "8 固定",
        "payload": "A",
        "structure": "二阶四边形；先 4 个角点，后 4 个边节点。",
        "faces": "无",
        "note": "当前包含 102、103、104。",
    },
    "QuadraticTriangle2D": {
        "category": "二维实体",
        "nodes": "6 固定",
        "payload": "A",
        "structure": "二阶三角形；先 3 个角点，后 3 个边节点。",
        "faces": "无",
        "note": "当前包含单相 11，以及 121、122。",
    },
    "PolygonSolid2D": {
        "category": "二维实体",
        "nodes": "不少于 3",
        "payload": "B",
        "structure": "二维多边形；无前言；可变长度平面节点列表。",
        "faces": "无",
        "note": "",
    },
    "EdgeStructured2D": {
        "category": "二维实体",
        "nodes": "可变",
        "payload": "D",
        "structure": (
            "443 使用 edge_count、逐边节点数、逐边节点；"
            "444/644 使用 edge_count、逐边阶次、角点、逐边内部节点。"
        ),
        "faces": "无",
        "note": "",
    },
    "Hexahedron": {
        "category": "三维实体",
        "nodes": "8 固定",
        "payload": "A",
        "structure": "8 节点六面体；前 4 个为底面角点，后 4 个为顶面角点。",
        "faces": "6 个四边形面",
        "note": "四面体退化签名：n3==n4 且 n5==n6==n7==n8。",
    },
    "HigherOrderHexahedron": {
        "category": "三维实体",
        "nodes": "20 固定",
        "payload": "A",
        "structure": "二阶六面体；角点、底边中点、竖边中点、顶边中点按约定排列。",
        "faces": "无",
        "note": "可由常规二阶转为 508/805/807。",
    },
    "HigherOrderWedge": {
        "category": "三维实体",
        "nodes": "15 固定",
        "payload": "A",
        "structure": "二阶三棱柱 A；竖边中点先于顶边中点。",
        "faces": "无",
        "note": "可由常规二阶转为 508/805/807。",
    },
    "HigherOrderWedgeAlt": {
        "category": "三维实体",
        "nodes": "15 固定",
        "payload": "A",
        "structure": "二阶三棱柱 B；顶边中点先于竖边中点。",
        "faces": "无",
        "note": "可由常规二阶转为 508/805/807。",
    },
    "Polyhedron": {
        "category": "三维实体",
        "nodes": "可变",
        "payload": "C",
        "structure": "面结构化多面体：face_count、每面节点数、按面展平节点。",
        "faces": "原样返回存储面",
        "note": "",
    },
    "HigherOrder": {
        "category": "三维实体",
        "nodes": "可变",
        "payload": "E",
        "structure": (
            "高阶多面体：n_faces、每面边数、每边阶次、节点；"
            "每面先写角点，再按边写内部节点。"
        ),
        "faces": "按结构字段重建",
        "note": "目标类型 508/805/807。",
    },
    "Slip2D": {
        "category": "二维接触面",
        "nodes": "4 固定",
        "payload": "A",
        "structure": "二维接触面；底面 2 节点 + 顶面 2 节点。",
        "faces": "无",
        "note": "",
    },
    "HexContact": {
        "category": "三维接触面",
        "nodes": "8 固定",
        "payload": "A",
        "structure": "8 节点六面体接触面；节点排序与 Hexahedron 相同。",
        "faces": "6 个四边形面",
        "note": "",
    },
    "Slip3D": {
        "category": "三维接触面",
        "nodes": "非空可变",
        "payload": "B",
        "structure": "t_id=22 的节点结构尚未明确，只保留平面节点列表。",
        "faces": "无",
        "note": "不推断角点、边点和阶次。",
    },
    "HigherOrderSlip3D": {
        "category": "三维接触面",
        "nodes": "16 固定",
        "payload": "A",
        "structure": "二阶空间四边形接触面；底角点、底边中点、顶角点、顶边中点。",
        "faces": "无",
        "note": "t_id=21 已从 Slip3D 中拆分。",
    },
    "PolygonContact": {
        "category": "三维接触面",
        "nodes": "偶数且不少于 6",
        "payload": "F",
        "structure": "多边形接触面；前半为底面，后半为顶面。",
        "faces": "底面、顶面和侧面",
        "note": "仅角点，无中边节点。",
    },
    "QuadStructuredContact": {
        "category": "三维接触面",
        "nodes": "8 + 2*sum(flags)",
        "payload": "G",
        "structure": "四边形跨阶接触面；4 个 0/1 中边节点标志，随后为底/顶层节点。",
        "faces": "无",
        "note": "",
    },
    "TriStructuredContact": {
        "category": "三维接触面",
        "nodes": "6 + 2*sum(flags)",
        "payload": "G",
        "structure": "三角形跨阶接触面；3 个 0/1 中边节点标志，随后为底/顶层节点。",
        "faces": "无",
        "note": "",
    },
}

PAYLOAD_DETAIL = [
    ("A", "固定长度平面节点列表", "无前言，节点数由具体类严格校验。"),
    ("B", "可变长度平面节点列表", "无前言，具体类校验最小长度或奇偶性。"),
    ("C", "面结构化多面体", "face_count, face_sizes..., face_nodes...。"),
    ("D", "边结构化二维单元", "443 与 444/644 的第二段含义不同，分别为每边节点数和每边阶次。"),
    ("E", "高阶多面体", "n_faces, face_edge_counts..., face_edge_orders..., face_nodes...。"),
    ("F", "多边形接触面", "偶数个角点；前半底面，后半顶面。"),
    ("G", "跨阶接触面", "3 或 4 个 0/1 标志，随后为压缩排列的底/顶节点。"),
]


def _style_header(ws, columns: int) -> None:
    for column in range(1, columns + 1):
        cell = ws.cell(row=1, column=column)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = THIN_BORDER
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")


def _style_range(ws, rows: int, columns: int) -> None:
    for row in range(2, rows + 1):
        for column in range(1, columns + 1):
            cell = ws.cell(row=row, column=column)
            cell.border = THIN_BORDER
            cell.alignment = WRAP_TOP


def _ids_text(values: list[int]) -> str:
    return ", ".join(str(value) for value in values)


def _response_ids_text(values: list[int], response_type: ElementResponseType) -> str:
    ids = [
        value
        for value in values
        if ELEMENT_RESPONSE_TYPE_BY_T_ID.get(value) == response_type
    ]
    return _ids_text(ids)


def registry_rows() -> list[dict[str, str]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    classes = {}
    for t_id, element_class in sorted(ELEMENT_TYPE_REGISTRY.items()):
        grouped[element_class.__name__].append(t_id)
        classes[element_class.__name__] = element_class

    rows = []
    for class_name in sorted(grouped, key=lambda name: min(grouped[name])):
        detail = CLASS_DETAIL[class_name]
        element_class = classes[class_name]
        rows.append({
            "class": class_name,
            "t_ids": _ids_text(grouped[class_name]),
            "single_phase": _response_ids_text(
                grouped[class_name], ElementResponseType.SINGLE_PHASE
            ),
            "saturated_porous_direct": _response_ids_text(
                grouped[class_name], ElementResponseType.SATURATED_POROUS_DIRECT
            ),
            "saturated_porous_staggered": _response_ids_text(
                grouped[class_name], ElementResponseType.SATURATED_POROUS_STAGGERED
            ),
            "category": detail["category"],
            "nodes": detail["nodes"],
            "payload": detail["payload"],
            "structure": detail["structure"],
            "faces": detail["faces"],
            "compatible": _ids_text(sorted(element_class.COMPATIBLE_TYPES)),
            "note": detail["note"],
        })
    return rows


def build_overview(wb: openpyxl.Workbook) -> None:
    ws = wb.active
    ws.title = "当前单元类型列表"
    headers = [
        "具体类",
        "当前注册 t_id",
        "单相",
        "饱和多孔介质直接求解",
        "饱和多孔介质交叉迭代",
        "分类",
        "节点约束",
        "Payload",
        "结构/节点顺序",
        "faces()",
        "COMPATIBLE_TYPES",
        "备注",
    ]
    for column, header in enumerate(headers, 1):
        ws.cell(row=1, column=column, value=header)
    _style_header(ws, len(headers))

    rows = registry_rows()
    for row_index, row in enumerate(rows, 2):
        values = [
            row["class"],
            row["t_ids"],
            row["single_phase"],
            row["saturated_porous_direct"],
            row["saturated_porous_staggered"],
            row["category"],
            row["nodes"],
            row["payload"],
            row["structure"],
            row["faces"],
            row["compatible"],
            row["note"],
        ]
        for column, value in enumerate(values, 1):
            ws.cell(row=row_index, column=column, value=value)
        if row["note"]:
            fill = NEW_FILL if "拆分" in row["note"] or "当前包含" in row["note"] else NOTE_FILL
            for column in range(1, len(headers) + 1):
                ws.cell(row=row_index, column=column).fill = fill

    _style_range(ws, len(rows) + 1, len(headers))
    widths = [24, 34, 18, 24, 24, 14, 22, 10, 72, 24, 34, 52]
    for column, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(column)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(rows) + 1}"


def build_payload_sheet(wb: openpyxl.Workbook) -> None:
    ws = wb.create_sheet("Payload格式")
    headers = ["Payload", "名称", "字段排列/校验说明", "涉及 t_id"]
    for column, header in enumerate(headers, 1):
        ws.cell(row=1, column=column, value=header)
    _style_header(ws, len(headers))

    rows_by_payload: dict[str, list[str]] = defaultdict(list)
    for row in registry_rows():
        rows_by_payload[row["payload"]].append(row["t_ids"])

    for row_index, (payload, name, rule) in enumerate(PAYLOAD_DETAIL, 2):
        ws.cell(row=row_index, column=1, value=payload)
        ws.cell(row=row_index, column=2, value=name)
        ws.cell(row=row_index, column=3, value=rule)
        ws.cell(row=row_index, column=4, value="; ".join(rows_by_payload[payload]))

    _style_range(ws, len(PAYLOAD_DETAIL) + 1, len(headers))
    widths = [10, 28, 76, 76]
    for column, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(column)].width = width
    ws.freeze_panes = "A2"


def build_flat_sheet(wb: openpyxl.Workbook) -> None:
    ws = wb.create_sheet("按t_id展开")
    headers = ["t_id", "具体类", "响应类型", "分类", "Payload", "节点约束"]
    for column, header in enumerate(headers, 1):
        ws.cell(row=1, column=column, value=header)
    _style_header(ws, len(headers))

    detail_by_class = CLASS_DETAIL
    for row_index, (t_id, element_class) in enumerate(sorted(ELEMENT_TYPE_REGISTRY.items()), 2):
        detail = detail_by_class[element_class.__name__]
        ws.cell(row=row_index, column=1, value=t_id)
        ws.cell(row=row_index, column=2, value=element_class.__name__)
        response_type = ELEMENT_RESPONSE_TYPE_BY_T_ID.get(t_id)
        ws.cell(
            row=row_index,
            column=3,
            value=response_type.label if response_type is not None else "未配置",
        )
        ws.cell(row=row_index, column=4, value=detail["category"])
        ws.cell(row=row_index, column=5, value=detail["payload"])
        ws.cell(row=row_index, column=6, value=detail["nodes"])

    _style_range(ws, len(ELEMENT_TYPE_REGISTRY) + 1, len(headers))
    widths = [12, 26, 28, 14, 10, 24]
    for column, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(column)].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{len(ELEMENT_TYPE_REGISTRY) + 1}"


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    wb = openpyxl.Workbook()
    build_overview(wb)
    build_payload_sheet(wb)
    build_flat_sheet(wb)
    for output in OUTPUTS:
        try:
            wb.save(output)
            print(f"已生成：{output}")
        except PermissionError:
            fallback = output.with_name(
                f"{output.stem}_current_{date.today():%Y%m%d}{output.suffix}"
            )
            wb.save(fallback)
            print(f"目标文件被占用，已生成：{fallback}")


if __name__ == "__main__":
    main()
