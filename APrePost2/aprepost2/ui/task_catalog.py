from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from aprepost2.services.hdf5 import merge_hdf5
from aprepost2.services.inversion import inversion_postprocess
from aprepost2.services.mesh_cutting import cut_mesh
from aprepost2.services.mesh_operations import (
    add_pore_constraints,
    change_all_fill_ids,
    change_element_types,
    export_element_mesh_by_material,
    export_elements_by_bounds,
    mesh_statistics,
    remap_fill_ids,
    remap_material_ids,
    scale_coordinates,
)
from aprepost2.services.search import search_nearest_elements, search_nearest_nodes
from aprepost2.services.result_reader import read_hdf5_results


@dataclass(frozen=True, slots=True)
class FieldSpec:
    name: str
    label: str
    kind: str = "text"
    default: str = ""
    file_filter: str = "所有文件 (*)"


@dataclass(frozen=True, slots=True)
class TaskSpec:
    key: str
    category: str
    title: str
    description: str
    fields: tuple[FieldSpec, ...]
    handler: Callable
    supports_overwrite: bool = False


MESH_FILTER = "网格文件 (*.dat);;所有文件 (*)"
CONTROL_FILTER = "控制文件 (*.txt *.dat);;所有文件 (*)"
H5_FILTER = "HDF5 文件 (*.h5 *.hdf5);;所有文件 (*)"
EXCEL_FILTER = "Excel 文件 (*.xlsx);;所有文件 (*)"


def _bounds_export(**values):
    bounds = tuple(values.pop(name) for name in ("xmin", "xmax", "ymin", "ymax", "zmin", "zmax"))
    return export_elements_by_bounds(bounds=bounds, **values)


TASKS = (
    TaskSpec(
        "clip",
        "前处理",
        "切割三维网格",
        "直接裁剪凸多面体并全局合并交点，不依赖外部可视化网格库。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "切割控制文件", "open", "control.txt", CONTROL_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_Inimesh.dat", MESH_FILTER),
            FieldSpec("tolerance", "容差", "float", "1e-6"),
        ),
        cut_mesh,
        True,
    ),
    TaskSpec(
        "nearest_node",
        "前处理",
        "检索最近节点",
        "使用空间索引检索测点的最近网格节点，并输出 Excel。",
        (
            FieldSpec("mesh_path", "网格文件", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "测点控制文件", "open", "control.txt", CONTROL_FILTER),
            FieldSpec("output_path", "输出 Excel", "save", "output_nodes.xlsx", EXCEL_FILTER),
        ),
        search_nearest_nodes,
        True,
    ),
    TaskSpec(
        "nearest_element",
        "前处理",
        "检索最近单元",
        "按允许材料号检索最近单元形心，并输出 Excel。",
        (
            FieldSpec("mesh_path", "网格文件", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "测点控制文件", "open", "control.txt", CONTROL_FILTER),
            FieldSpec("output_path", "输出 Excel", "save", "output_elements.xlsx", EXCEL_FILTER),
        ),
        search_nearest_elements,
        True,
    ),
    TaskSpec(
        "pore",
        "前处理",
        "按材料交界添加孔压约束",
        "单遍历建立节点—材料邻接关系，在指定材料交界节点添加孔压约束。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "材料对控制文件", "open", "control.dat", CONTROL_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_Inimesh.dat", MESH_FILTER),
        ),
        add_pore_constraints,
        True,
    ),
    TaskSpec(
        "element_type",
        "前处理",
        "按材料修改单元类型",
        "仅对控制文件指定材料中的单元执行类型映射。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "转换控制文件", "open", "control.dat", CONTROL_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_Inimesh.dat", MESH_FILTER),
        ),
        change_element_types,
        True,
    ),
    TaskSpec(
        "material",
        "前处理",
        "修改材料号",
        "按“旧材料号 新材料号”映射批量修改。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "材料映射文件", "open", "control.dat", CONTROL_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_Inimesh.dat", MESH_FILTER),
        ),
        remap_material_ids,
        True,
    ),
    TaskSpec(
        "fill",
        "前处理",
        "修改填筑号",
        "按“旧填筑号 新填筑号”映射批量修改。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "填筑号映射文件", "open", "control.dat", CONTROL_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_Inimesh.dat", MESH_FILTER),
        ),
        remap_fill_ids,
        True,
    ),
    TaskSpec(
        "all_fill",
        "前处理",
        "统一所有填筑号",
        "将全部单元的填筑号 c_id 设置为同一数值。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("fill_id", "统一填筑号", "int", "0"),
            FieldSpec("output_path", "输出网格", "save", "out_Inimesh.dat", MESH_FILTER),
        ),
        change_all_fill_ids,
        True,
    ),
    TaskSpec(
        "scale",
        "前处理",
        "节点坐标缩放",
        "在指定方向和范围内相对基准点缩放，范围外平移以保持连续。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "缩放控制文件", "open", "control.txt", CONTROL_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_Inimesh.dat", MESH_FILTER),
        ),
        scale_coordinates,
        True,
    ),
    TaskSpec(
        "bounds",
        "前处理",
        "按范围输出单元",
        "按闭区间形心范围输出单元及其引用节点，不改变编号和连接顺序。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("xmin", "X 最小值", "float", "-1e30"),
            FieldSpec("xmax", "X 最大值", "float", "1e30"),
            FieldSpec("ymin", "Y 最小值", "float", "-1e30"),
            FieldSpec("ymax", "Y 最大值", "float", "1e30"),
            FieldSpec("zmin", "Z 最小值", "float", "-1e30"),
            FieldSpec("zmax", "Z 最大值", "float", "1e30"),
            FieldSpec("output_path", "输出网格", "save", "selected.dat", MESH_FILTER),
        ),
        _bounds_export,
        True,
    ),
    TaskSpec(
        "material_export",
        "前处理",
        "按材料输出单元网格",
        "根据控制文件中列出的材料编号，为每种材料分别输出包含对应单元及其引用节点的独立网格文件。"
        "输出文件命名为“基础文件名_material_材料号.扩展名”。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "材料列表控制文件", "open", "material_list.txt", CONTROL_FILTER),
            FieldSpec("output_path", "输出基础文件名", "save", "out_material.dat", MESH_FILTER),
        ),
        export_element_mesh_by_material,
        True,
    ),
    TaskSpec(
        "merge_h5",
        "后处理",
        "合并 HDF5",
        "保留第一个文件完整结构，并合并第二个文件的 frames。",
        (
            FieldSpec("first_path", "第一个 HDF5", "open", "static1.h5", H5_FILTER),
            FieldSpec("second_path", "第二个 HDF5", "open", "static2.h5", H5_FILTER),
            FieldSpec("output_path", "输出 HDF5", "save", "static.h5", H5_FILTER),
        ),
        merge_hdf5,
        True,
    ),
    TaskSpec(
        "read_h5",
        "后处理",
        "读取 HDF5 节点/单元结果",
        "按控制文件分块读取计算结果并输出节点、单元时程及统计量。",
        (
            FieldSpec("control_path", "控制文件", "open", "control.txt", CONTROL_FILTER),
            FieldSpec("hdf5_path", "结果 HDF5", "open", "static.h5", H5_FILTER),
            FieldSpec("mesh_path", "网格文件", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("output_prefix", "输出文件前缀", "save", "output", "所有文件 (*)"),
        ),
        read_hdf5_results,
        True,
    ),
    TaskSpec(
        "inversion",
        "后处理",
        "反演后处理",
        "读取反演控制工作簿和测点结果，完成插值、对比与输出。",
        (
            FieldSpec("control_path", "控制工作簿", "open", "control.xlsx", "Excel 文件 (*.xlsx *.xls)"),
            FieldSpec("file_count", "文件数量", "int", "1"),
            FieldSpec("dimension", "维度（2 或 3）", "int", "3"),
            FieldSpec("output_directory", "输出目录", "directory", "."),
        ),
        inversion_postprocess,
        True,
    ),
    TaskSpec(
        "stats",
        "前处理",
        "网格统计",
        "统计各材料/各单元类型的单元与节点数量，以及孔压节点数，输出到 Excel。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("output_path", "输出 Excel", "save", "mesh_statistics.xlsx", EXCEL_FILTER),
        ),
        mesh_statistics,
        True,
    ),
)

TASK_BY_KEY = {task.key: task for task in TASKS}
