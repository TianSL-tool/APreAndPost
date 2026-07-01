"""生成单元类型 Excel 对比表 —— 供人工审核读取/写出逻辑."""
from __future__ import annotations

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

OUTPUT = Path(__file__).resolve().parent.parent / "docs" / "单元类型对比表.xlsx"
OUTPUT.parent.mkdir(parents=True, exist_ok=True)

# ── 样式 ──────────────────────────────────────────────────
HEADER_FONT = Font(name="微软雅黑", bold=True, size=10, color="FFFFFF")
HEADER_FILL = PatternFill(start_color="4472C4", end_color="4472C4", fill_type="solid")
SECTION_FILL = PatternFill(start_color="D6E4F0", end_color="D6E4F0", fill_type="solid")
WARN_FILL = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
THIN_BORDER = Border(
    left=Side(style="thin"), right=Side(style="thin"),
    top=Side(style="thin"), bottom=Side(style="thin"),
)
WRAP = Alignment(wrap_text=True, vertical="top")


def style_header(ws, row, ncols):
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
        cell.border = THIN_BORDER


def style_data(ws, start_row, end_row, ncols):
    for r in range(start_row, end_row + 1):
        for c in range(1, ncols + 1):
            cell = ws.cell(row=r, column=c)
            cell.border = THIN_BORDER
            cell.alignment = WRAP


# ── 数据定义 ───────────────────────────────────────────────

# 按 payload 格式分类:
# A = 固定长度平面节点列表
# B = 可变长度平面节点列表
# C = 面数 + 每面节点数 + 展平节点ID (Polyhedron)
# D = 边数 + 每边节点数 + 节点ID (EdgeStructured2D)
# E = 面数 + 每面边数 + 每边阶数 + 节点ID (HigherOrder)
# F = 底面 + 顶面分半 (PolygonContact / Slip2D 概念上)
# G = 前言元数据 + 节点ID (StructuredContact)

ELEMENTS = [
    # ── 二维实体 ──
    {"t_id": "1, 2, 102, 222", "old_class": "ElementType1", "new_class": "QuadSolid2D",
     "category": "二维实体", "nodes": "4 (固定)", "format": "A",
     "structure": "4 节点四边形，平面节点列表，无前言",
     "faces": "无", "compat": "1, 2, 222"},
    {"t_id": "44, 47, 470", "old_class": "ElementType44", "new_class": "PolygonSolid2D",
     "category": "二维实体", "nodes": "可变", "format": "B",
     "structure": "N 节点多边形，平面节点列表，无前言",
     "faces": "无", "compat": "44, 47, 470"},
    {"t_id": "443, 444, 644", "old_class": "ElementType444", "new_class": "EdgeStructured2D",
     "category": "二维实体", "nodes": "可变 (Σ每边节点数)", "format": "D",
     "structure": "边数前言 + 每边节点数 + 按边排列的节点ID",
     "faces": "无", "compat": "443, 444, 644"},

    # ── 三维实体 - 六面体 ──
    {"t_id": "5, 6, 23, 61, 500", "old_class": "ElementType6", "new_class": "Hexahedron",
     "category": "三维实体", "nodes": "8 (固定)", "format": "A",
     "structure": "8 节点六面体: 前4=底面(CCW), 后4=顶面(CCW)。faces()返回6个四边形面",
     "faces": "6 四边形面", "compat": "5, 6, 23, 61, 500"},

    # ── 三维实体 - 平面节点列表 ──
    {"t_id": "16, 18, 20, 170, 171, 190, 191, 510, 511",
     "old_class": "ElementType16or510or511 / ElementType18or170or171 / ElementType30or190or191",
     "new_class": "Solid3DOther",
     "category": "三维实体", "nodes": "可变", "format": "B",
     "structure": "平面节点列表，无显式面拓扑。旧工程分3个子类但解析逻辑完全一致（全部继承SolidElement3D.read_points）",
     "faces": "无", "compat": "类内互转(同Python类)"},

    # ── 三维实体 - 多面体 ──
    {"t_id": "53, 57, 59, 80, 800", "old_class": "ElementType57or59", "new_class": "Polyhedron",
     "category": "三维实体", "nodes": "可变 (Σ每面节点数)", "format": "C",
     "structure": "面数 + 每面节点数(每值≥3) + 按面展平的节点ID。faces()直接返回存储的面元组",
     "faces": "直接返回存储的面", "compat": "53, 57, 59, 80, 800"},

    # ── 三维实体 - 高阶多面体 ──
    {"t_id": "508, 805, 807", "old_class": "ElementType508", "new_class": "HigherOrder",
     "category": "三维实体", "nodes": "可变 (Σ每面各边阶数之和)", "format": "E",
     "structure": (
         "三层嵌套: 面数→每面边数→每边多项式阶数→节点ID。"
         "每面节点数=该面各边阶数之和(非边数)。"
         "faces()按_nodes_per_face延迟重建。⚠ 2026-07-01修复: total_nodes从sum(face_sizes)改为sum(sum(orders))"
     ),
     "faces": "按节点数切片重建", "compat": "类内互转", "note": "已修复节点数校验bug"},

    # ── 二维接触面 ──
    {"t_id": "4, 700, 777", "old_class": "ElementType4", "new_class": "Slip2D",
     "category": "二维接触面", "nodes": "可变 (偶数)", "format": "B",
     "structure": "平面节点列表。概念上前半=底面、后半=顶面(但未显式存储)。旧工程无faces()方法",
     "faces": "无", "compat": "4, 700, 777"},

    # ── 三维接触面 - 六面体接触 ──
    {"t_id": "9, 902, 903", "old_class": "ElementType9", "new_class": "HexContact",
     "category": "三维接触面", "nodes": "8 (固定)", "format": "A",
     "structure": "8节点六面体接触面。faces()与Hexahedron完全相同(6个四边形面)。旧工程支持退化为三棱柱(节点2==节点3时)",
     "faces": "6 四边形面", "compat": "9, 902, 903",
     "note": "旧工程支持三角退化，新工程未实现"},

    # ── 三维接触面 - 平面节点列表 ──
    {"t_id": "21, 22", "old_class": "ElementType21 / ElementType22", "new_class": "Slip3D",
     "category": "三维接触面", "nodes": "可变", "format": "B",
     "structure": "平面节点列表，无显式面拓扑。旧工程分2个子类但解析逻辑完全一致",
     "faces": "无", "compat": "类内互转"},

    # ── 三维接触面 - 多边形接触 ──
    {"t_id": "60, 601, 602", "old_class": "ElementType60", "new_class": "PolygonContact",
     "category": "三维接触面", "nodes": "可变 (偶数)", "format": "F",
     "structure": (
         "节点数必须为偶数。前半=底面节点, 后半=顶面节点。"
         "faces()返回: 底面(reversed)+顶面+N个侧面四边形。"
         "topology_payload()返回平面节点列表(无前言)"
     ),
     "faces": "底面+顶面+侧面四边形", "compat": "60, 601, 602"},

    # ── 三维接触面 - 结构化接触 ──
    {"t_id": "223, 224", "old_class": "ElementType223 / ElementType224",
     "new_class": "StructuredContact",
     "category": "三维接触面", "nodes": "可变", "format": "G",
     "structure": "前言元数据(t_id=223→4个int, t_id=224→3个int) + 平面节点列表。旧工程存为self.num_mid",
     "faces": "无", "compat": "类内互转"},
]

FORMAT_DETAIL = [
    ("A", "固定长度平面节点列表",
     "payload = [n1, n2, ..., nK]  (K固定)",
     "无校验，直接作为node_ids",
     "1,2,102,222 (K=4); 5,6,23,61,500 (K=8); 9,902,903 (K=8)"),
    ("B", "可变长度平面节点列表",
     "payload = [n1, n2, ..., nN]  (N可变)",
     "无校验，全部作为node_ids",
     "4,700,777; 16,18,20,170,171,190,191,510,511; 21,22; 44,47,470"),
    ("C", "多面体：面数+每面节点数+展平节点ID",
     "face_count, cnt_0, ..., cnt_{F-1}, n_00, n_01, ..., n_{F-1, cnt_{F-1}-1}",
     "face_count≥4; 每面cnt≥3; Σcnt = len(节点ID)",
     "53,57,59,80,800"),
    ("D", "边结构化二维：边数+每边节点数+节点ID",
     "edge_count, size_0, ..., size_{E-1}, n_0, n_1, ..., n_{N-1}",
     "edge_count≥3; payload长度≥1+edge_count",
     "443,444,644"),
    ("E", "高阶多面体：面数+每面边数+每边阶数+节点ID",
     "face_count, edges_0, ..., edges_{F-1}, order_{0,0}, ..., order_{F-1,edges_{F-1}-1}, n_0, ..., n_{N-1}",
     "face_count≥4; Σ每面边阶数之和 = len(节点ID); 每面节点数≠每面边数",
     "508,805,807"),
    ("F", "多边形接触面：等分两半(底面+顶面)",
     "b_0, ..., b_{half-1}, t_0, ..., t_{half-1}  (总数为偶数)",
     "节点总数必须为偶数; 隐式对半分为底面和顶面",
     "60,601,602"),
    ("G", "结构化接触面：前言元数据+节点ID",
     "mid_0, ..., mid_{k-1}, n_0, ..., n_{N-1}  (k=4 for 223, k=3 for 224)",
     "payload长度≥k+1; k由_PREAMBLE_SIZE类变量确定",
     "223(k=4), 224(k=3)"),
]

DIFF = [
    ("1, 2, 102, 222", "QuadSolid2D vs ElementType1",
     "from_parsed()与read_points()逻辑一致: payload全部作为node_ids",
     "新工程无faces(); 旧工程隐式4边形，无显式faces",
     "✅ 一致", ""),
    ("44, 47, 470", "PolygonSolid2D vs ElementType44",
     "一致: payload全部作为node_ids",
     "均无faces()",
     "✅ 一致", ""),
    ("443, 444, 644", "EdgeStructured2D vs ElementType444",
     "一致: 解析edge_count + per-edge sizes + node_ids。旧工程存self.bian/self.bian_num; 新工程存_edge_count/_edge_sizes",
     "均无faces()",
     "✅ 一致", ""),
    ("5, 6, 23, 61, 500", "Hexahedron vs ElementType6",
     "一致: 8节点平面列表",
     "新工程faces()返回6个四边形面(顺序: bottom, top, front, right, back, left)。旧工程get_6type_basic_faces()通过索引[0,1,2,3],[4,5,6,7]...隐式定义，需确认面朝向一致",
     "⚠ 需验证面朝向", "旧工程可用于切割(可转t_id=57); 新工程COMPATIBLE_TYPES包含5,6,23,61,500"),
    ("16, 18, 20, 170, 171, 190, 191, 510, 511", "Solid3DOther (合并3个旧类)",
     "一致: 全部作为node_ids。旧工程3个独立子类但read_points()逻辑完全一致(均继承SolidElement3D)",
     "均无faces()",
     "✅ 一致", "新工程统一为1个类，9个t_id"),
    ("53, 57, 59, 80, 800", "Polyhedron vs ElementType57or59",
     "一致: face_count + per-face counts + flattened nodes。旧工程存self.mian/self.mianDian; 新工程存_faces",
     "新工程faces()直接返回存储的面。旧工程通过self.mianDian访问",
     "✅ 一致", "旧工程含turn_57_to_60()转换逻辑(切割后处理)"),
    ("508, 805, 807", "HigherOrder vs ElementType508",
     "两者均为: face_count + per-face edge_count + per-edge orders + node_ids。关键差异: 旧工程每面节点数=sum(face_orders); 新工程(修复后)一致",
     "新工程faces()按_nodes_per_face切片重建。旧工程通过self.mianDian[face_i]访问",
     "⚠ 2026-07-01修复后一致", "修复前total_nodes=sum(face_sizes)导致校验失败"),
    ("4, 700, 777", "Slip2D vs ElementType4",
     "一致: payload为平面节点列表。旧工程概念上前半=底后半=顶但无显式存储",
     "新工程无faces(); 旧工程无显式faces方法",
     "✅ 一致", ""),
    ("9, 902, 903", "HexContact vs ElementType9",
     "一致: 8节点平面列表",
     "新工程faces()与Hexahedron完全相同。旧工程有to_element60()退化处理(节点2==3时为三棱柱)。新工程未实现退化检测",
     "⚠ 缺少退化检测", ""),
    ("21, 22", "Slip3D (合并2个旧类)",
     "一致: payload为平面节点列表",
     "均无faces()",
     "✅ 一致", "新工程统一为1个类"),
    ("60, 601, 602", "PolygonContact vs ElementType60",
     "一致: payload为平面节点列表(偶数个), 隐式前半=底后半=顶。旧工程存self.half_num",
     "新工程faces()返回bottom+top+lateral quads。旧工程通过half_num隐式划分",
     "✅ 一致", "旧工程ElementType6/9可转为60"),
    ("223", "StructuredContact vs ElementType223",
     "一致: 4个前言元数据+节点ID。旧工程存self.num_mid(长度为4); 新工程存_mid_info",
     "均无faces()",
     "✅ 一致", ""),
    ("224", "StructuredContact vs ElementType224",
     "一致: 3个前言元数据+节点ID",
     "均无faces()",
     "✅ 一致", ""),
]


def build_sheet1(wb):
    ws = wb.active
    ws.title = "单元类型总览"
    headers = ["t_id", "旧工程类名", "新工程类名", "分类", "节点数",
               "Payload格式", "结构特征(排序规则)", "faces()", "COMPATIBLE_TYPES", "备注"]
    for c, h in enumerate(headers, 1):
        ws.cell(row=1, column=c, value=h)
    style_header(ws, 1, len(headers))

    for i, e in enumerate(ELEMENTS, 2):
        ws.cell(row=i, column=1, value=e["t_id"])
        ws.cell(row=i, column=2, value=e["old_class"])
        ws.cell(row=i, column=3, value=e["new_class"])
        ws.cell(row=i, column=4, value=e["category"])
        ws.cell(row=i, column=5, value=e["nodes"])
        ws.cell(row=i, column=6, value=e["format"])
        ws.cell(row=i, column=7, value=e["structure"])
        ws.cell(row=i, column=8, value=e["faces"])
        ws.cell(row=i, column=9, value=e["compat"])
        ws.cell(row=i, column=10, value=e.get("note", ""))
        if e.get("note"):
            for c in range(1, len(headers) + 1):
                ws.cell(row=i, column=c).fill = WARN_FILL
    style_data(ws, 2, 1 + len(ELEMENTS), len(headers))
    ws.column_dimensions["A"].width = 24
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 22
    ws.column_dimensions["D"].width = 14
    ws.column_dimensions["E"].width = 28
    ws.column_dimensions["F"].width = 10
    ws.column_dimensions["G"].width = 60
    ws.column_dimensions["H"].width = 22
    ws.column_dimensions["I"].width = 26
    ws.column_dimensions["J"].width = 26
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}{1 + len(ELEMENTS)}"


def build_sheet2(wb):
    ws = wb.create_sheet("Payload格式详解")
    headers = ["格式", "名称", "字段排列", "校验规则", "涉及 t_id"]
    for c, h in enumerate(headers, 1):
        ws.cell(row=1, column=c, value=h)
    style_header(ws, 1, len(headers))

    for i, d in enumerate(FORMAT_DETAIL, 2):
        for c, v in enumerate(d, 1):
            ws.cell(row=i, column=c, value=v)
    style_data(ws, 2, 1 + len(FORMAT_DETAIL), len(headers))
    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 28
    ws.column_dimensions["C"].width = 70
    ws.column_dimensions["D"].width = 50
    ws.column_dimensions["E"].width = 50
    ws.freeze_panes = "A2"


def build_sheet3(wb):
    ws = wb.create_sheet("新旧对比差异")
    headers = ["t_id", "类名对比", "解析逻辑对比 (from_parsed vs read_points)",
               "拓扑/faces()对比", "一致性", "备注"]
    for c, h in enumerate(headers, 1):
        ws.cell(row=1, column=c, value=h)
    style_header(ws, 1, len(headers))

    for i, d in enumerate(DIFF, 2):
        for c, v in enumerate(d, 1):
            ws.cell(row=i, column=c, value=v)
        # 高亮不一致的
        if "⚠" in str(d[4]):
            for c in range(1, len(headers) + 1):
                ws.cell(row=i, column=c).fill = WARN_FILL
    style_data(ws, 2, 1 + len(DIFF), len(headers))
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 30
    ws.column_dimensions["C"].width = 55
    ws.column_dimensions["D"].width = 50
    ws.column_dimensions["E"].width = 22
    ws.column_dimensions["F"].width = 40
    ws.freeze_panes = "A2"


def main():
    wb = openpyxl.Workbook()
    build_sheet1(wb)
    build_sheet2(wb)
    build_sheet3(wb)
    wb.save(OUTPUT)
    print(f"Done: {OUTPUT}")


if __name__ == "__main__":
    main()
