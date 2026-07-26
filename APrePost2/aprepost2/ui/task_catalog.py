from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from aprepost2.services.hdf5 import merge_hdf5
from aprepost2.services.hdf5_material_filter import delete_hdf5_data_by_element_ids
from aprepost2.services.inversion import inversion_postprocess
from aprepost2.services.mesh_cutting import cut_mesh
from aprepost2.services.mesh_section import extract_mesh_section
from aprepost2.services.mesh_operations import (
    convert_to_higher_order,
    add_pore_constraints,
    change_all_fill_ids,
    change_element_types,
    convert_element_types_by_material,
    delete_elements_by_material,
    export_element_mesh_by_material,
    export_elements_by_bounds,
    mesh_statistics,
    merge_close_nodes,
    offset_mesh_ids,
    remap_fill_ids,
    remap_material_ids,
    scale_all_nodes_by_center_node,
    scale_coordinates,
)
from aprepost2.services.restart_export import export_restart_element_gauss_data
from aprepost2.services.search import search_nearest_elements, search_nearest_nodes
from aprepost2.services.result_reader import read_hdf5_results
from aprepost2.services.tecplot_merge import (
    merge_tecplot_single_step,
    merge_tecplot_step_series,
)


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
        "mesh_section",
        "前处理",
        "抽取三维网格截面",
        "用原点和法向量定义平面，将线性三维实体和 9 系列三维接触面抽取为二维截面网格。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("origin_x", "截面原点 X", "float", "0"),
            FieldSpec("origin_y", "截面原点 Y", "float", "0"),
            FieldSpec("origin_z", "截面原点 Z", "float", "0"),
            FieldSpec("normal_x", "法向量 X", "float", "1"),
            FieldSpec("normal_y", "法向量 Y", "float", "0"),
            FieldSpec("normal_z", "法向量 Z", "float", "0"),
            FieldSpec("material_ids", "材料号（all 或整数列表）", "text", "all"),
            FieldSpec("tolerance", "几何容差", "float", "1e-6"),
            FieldSpec(
                "output_path", "输出截面网格", "save", "section.dat", MESH_FILTER
            ),
        ),
        extract_mesh_section,
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
        "element_topology_conversion",
        "前处理",
        "按材料单元互转",
        "按材料号和旧/新类型执行安全拓扑互转，支持常规二维/三维与多边形、多面体、高阶结构化之间的常用转换。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "转换控制文件", "open", "control.dat", CONTROL_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_Inimesh.dat", MESH_FILTER),
        ),
        convert_element_types_by_material,
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
        "节点坐标局部缩放",
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
        "scale_by_center_node",
        "前处理",
        "以节点为中心缩放所有节点",
        "以控制文件指定节点的当前坐标为中心，对全部节点进行整体缩放。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "中心节点缩放控制文件", "open", "control.txt", CONTROL_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_Inimesh.dat", MESH_FILTER),
        ),
        scale_all_nodes_by_center_node,
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
        "根据控制文件中列出的材料编号，将对应材料的单元及其引用节点合并输出到一个网格文件中。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "材料列表控制文件", "open", "material_list.txt", CONTROL_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_material.dat", MESH_FILTER),
        ),
        export_element_mesh_by_material,
        True,
    ),
    TaskSpec(
        "material_delete",
        "前处理",
        "按材料删除单元",
        "根据控制文件中列出的材料编号，删除对应材料的所有单元，保留其余单元及其引用节点。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("control_path", "材料列表控制文件", "open", "material_list.txt", CONTROL_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_deleted.dat", MESH_FILTER),
        ),
        delete_elements_by_material,
        True,
    ),
    TaskSpec(
        "offset_mesh_ids",
        "前处理",
        "节点/单元编号整体偏移",
        "分别给全部节点号和单元号增加指定整数，并同步更新所有单元中的节点连接编号。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("node_id_offset", "节点号增加值", "int", "0"),
            FieldSpec("element_id_offset", "单元号增加值", "int", "0"),
            FieldSpec(
                "output_path",
                "输出网格",
                "save",
                "out_offset_ids.dat",
                MESH_FILTER,
            ),
        ),
        offset_mesh_ids,
        True,
    ),
    TaskSpec(
        "merge_close_nodes",
        "前处理",
        "按距离合并节点",
        "使用空间索引合并距离小于给定值的节点，并同步更新全部单元连接编号。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("distance_tolerance", "合并距离", "float", "1e-6"),
            FieldSpec(
                "output_path",
                "输出网格",
                "save",
                "out_merged_nodes.dat",
                MESH_FILTER,
            ),
        ),
        merge_close_nodes,
        True,
    ),
    TaskSpec(
        "higher_order_convert",
        "前处理",
        "常规高阶转任意高阶",
        "将常规高阶单元（平面节点列表）转换为面结构化的任意高阶单元（508/805/807）。"
        "映射：16,18,20→508；510,170,190→805；511,171,191→807。",
        (
            FieldSpec("input_path", "输入网格", "open", "Inimesh.dat", MESH_FILTER),
            FieldSpec("output_path", "输出网格", "save", "out_higher_order.dat", MESH_FILTER),
        ),
        convert_to_higher_order,
        True,
    ),
    TaskSpec(
        "plt_step_merge",
        "后处理",
        "PLT 单步提取与合并",
        "从文件、多个文件夹或递归扫描结果中选择 Tecplot ASCII .plt 文件，"
        "提取同一 Zone 步并按可编辑工况顺序合并。",
        (),
        merge_tecplot_single_step,
        True,
    ),
    TaskSpec(
        "plt_step_series_merge",
        "\u540e\u5904\u7406",
        "PLT \u5206\u6b65\u6587\u4ef6\u6279\u91cf\u5408\u5e76",
        "\u6309\u6587\u4ef6\u540d\u672b\u5c3e\u8ba1\u7b97\u6b65\u5206\u7ec4\uff0c"
        "\u5c06\u540c\u4e00\u8f93\u51fa\u540d\u7684\u5355 Zone PLT "
        "\u6309\u6570\u503c\u6b65\u53f7\u5408\u5e76\u3002",
        (),
        merge_tecplot_step_series,
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
        "restart_gauss_export",
        "后处理",
        "导出重启动单元高斯点数据",
        "从 output_for_restart 结构读取指定单元，按高斯点导出应力、应变和本构内变量到 Excel。",
        (
            FieldSpec("hdf5_path", "重启动 HDF5", "open", "static_57_for_restart.h5", H5_FILTER),
            FieldSpec("restart_step", "重启动步号", "text", "auto"),
            FieldSpec("element_ids", "单元号列表", "text", "16385, 16386"),
            FieldSpec("output_path", "输出 Excel", "save", "restart_gauss_data.xlsx", EXCEL_FILTER),
        ),
        export_restart_element_gauss_data,
        True,
    ),
    TaskSpec(
        "hdf5_element_delete",
        "后处理",
        "按单元号删除初始/重启动数据",
        "从初始条件或重启动 HDF5 的 element_info 中删除单元号文件指定的单元，"
        "并同步删除对应高斯点的应力、应变和本构内变量。",
        (
            FieldSpec("input_path", "输入 HDF5", "open", "static_for_init.h5", H5_FILTER),
            FieldSpec(
                "group_path",
                "数据组路径",
                "text",
                "auto",
            ),
            FieldSpec(
                "element_ids_path",
                "待删除单元号文件",
                "open",
                "element_ids.txt",
                CONTROL_FILTER,
            ),
            FieldSpec(
                "output_path",
                "输出 HDF5",
                "save",
                "static_elements_deleted.h5",
                H5_FILTER,
            ),
        ),
        delete_hdf5_data_by_element_ids,
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


CONTROL_FILE_HELP: dict[str, str] = {
    "plt_step_merge": """配置说明：PLT 单步提取与合并
本功能无需制作控制文件，全部参数直接在专用窗口中设置。
1. “添加文件”可跨文件夹选择多个 .plt 文件。
2. “添加多个文件夹”扫描各所选文件夹的当前层；“递归扫描”同时扫描子文件夹。
3. 计算步按每个文件内 Zone 的顺序从 1 开始计数，例如填写 3 表示提取第 3 个 Zone。
4. 表格中的工况名称可编辑；最终 Zone 顺序以表格从上到下的顺序为准。
5. “复制工况”会再次引用同一个只读源文件，可用于让基准工况在结果中多次出现。
6. 文件夹内有多个不同名 .plt 时会全部展开到表格，并以完整路径区分；可按需移除和排序。
7. 输出必须是新文件；若目标已存在，需明确确认覆盖。
执行前会检查每个文件是否存在指定步，以及 VARIABLES 的数量、名称和顺序是否一致。
原始 .plt 文件只读，不会被修改。""",
    "clip": """控制文件制作说明：切割三维网格
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
格式：
第 1 行：最大单元边长，必须 > 0，用于确定切割面附近搜索距离。
第 2 行：切割面数量 n。
每个切割面依次写：
  材料数量 m；若 m=0 表示不按材料筛选。
  m 行材料号。
  1 行范围：xmin xmax ymin ymax zmin zmax。
  3 行切割面上的三个点：x y z；三点不能共线。
最后 1 行可选：边界处理模式，0=关闭，1=默认协调，2=更严格协调；不写时默认为 1。
示例：
1.0
1
0
-10 10 -10 10 -10 10
0.5 0 0
0.5 1 0
0.5 0 1
1""",
    "nearest_node": """控制文件制作说明：检索最近节点
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
第 1 行：测点数量 n。
之后 n 行：测点标签 测点ID x y z。
示例：
2
P1 1001 0.0 0.0 0.0
P2 1002 10.0 5.0 0.0""",
    "nearest_element": """控制文件制作说明：检索最近单元
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
第 1 行：测点数量 n。
之后 n 行：测点标签 测点ID x y z 材料号1 材料号2 ...
程序只在该行列出的材料号内寻找最近单元形心。
示例：
2
P1 1001 0.0 0.0 0.0 1
P2 1002 10.0 5.0 0.0 2 3""",
    "pore": """控制文件制作说明：按材料交界添加孔压约束
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
第 1 行：材料对数量 n。
之后 n 行：材料号A 材料号B。
如果某个节点同时被材料 A 和材料 B 的单元引用，则该节点 press 置为 1。
示例：
2
1 2
3 4""",
    "element_type": """控制文件制作说明：按材料修改单元类型
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
格式：
第 1 行：材料数量 m。
之后 m 行：需要处理的材料号。
下一行：类型映射数量 n。
之后 n 行：旧单元类型 新单元类型。
示例：
1
5
2
6 57
11 102""",
    "element_topology_conversion": """控制文件制作说明：按材料单元互转
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
格式与“按材料修改单元类型”一致：
第 1 行：材料数量 m。
之后 m 行：需要处理的材料号。
下一行：类型映射数量 n。
之后 n 行：旧单元类型 新单元类型。
目标类型 0 仅表示常规高阶自动转任意高阶结构；其他类型需满足程序支持的拓扑转换表。
示例：
2
5
6
1
57 6""",
    "material": """控制文件制作说明：修改材料号
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
第 1 行：映射数量 n。
之后 n 行：旧材料号 新材料号。
示例：
2
1 101
2 102""",
    "fill": """控制文件制作说明：修改填筑号
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
第 1 行：映射数量 n。
之后 n 行：旧填筑号 新填筑号。
示例：
2
0 1
1 2""",
    "scale": """控制文件制作说明：节点坐标局部缩放
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
采用 key=value 格式，必须包含：
BASE_POINT=x y z
SCALE_DIR=x 或 y 或 z
SCALE_RANGE_MIN=范围下限
SCALE_RANGE_MAX=范围上限
SCALE_FACTOR=缩放系数，必须 > 0
示例：
BASE_POINT=0 0 0
SCALE_DIR=z
SCALE_RANGE_MIN=0
SCALE_RANGE_MAX=100
SCALE_FACTOR=1.2""",
    "scale_by_center_node": """控制文件制作说明：以节点为中心缩放所有节点
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
采用 key=value 格式，必须包含 CENTER_NODE_ID。
可写 SCALE_FACTOR 作为统一缩放系数；也可写 SCALE_X、SCALE_Y、SCALE_Z 分方向覆盖。
所有缩放系数必须 > 0。
示例：
CENTER_NODE_ID=100
SCALE_FACTOR=1.0
SCALE_X=1.1
SCALE_Y=1.1
SCALE_Z=0.95""",
    "material_export": """控制文件制作说明：按材料输出单元网格
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
第 1 行：材料数量 n。
之后 n 行：材料号。
程序会输出这些材料的单元以及被这些单元引用的节点。
示例：
3
1
2
5""",
    "material_delete": """控制文件制作说明：按材料删除单元
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
第 1 行：材料数量 n。
之后 n 行：材料号。
程序会删除这些材料的单元，并保留其余单元引用到的节点。
示例：
2
1
5""",
    "read_h5": """控制文件制作说明：读取 HDF5 节点/单元结果
通用规则：空行、以 # 或 // 开头的注释行会被忽略。
采用包含关键字的 key=value 行，常用项如下：
output node number = 节点数量；其后逐行写节点号。
output element number = 单元数量；其后逐行写单元号。
output step number = 步数量；其后逐行写步号。
base node = 基准节点号；0 表示不使用基准节点。
podu = 坡度角或派生量计算参数。
initial stress = 1 保留初始应力，0 扣除初始应力。
initial strain = 1 保留初始应变，0 扣除初始应变。
示例：
output node number = 2
1001
1002
output element number = 1
2001
output step number = 3
1
10
20
base node = 0
podu = 0
initial stress = 1
initial strain = 1""",
    "hdf5_element_delete": """控制文件制作说明：按单元号删除初始/重启动数据
单元号文件支持两种写法，空行、#、// 注释会被忽略。
写法 1：直接列出单元号，可用空格、逗号或换行分隔。
写法 2：首个数字为后续单元号数量，后面逐个写单元号。
示例 1：
1001 1002 1003
示例 2：
3
1001
1002
1003
数据组路径可填 auto；若文件有多个候选组，请填写类似 output_for_restart/57 或 output_for_initial_condition/100。""",
    "inversion": """控制工作簿制作说明：反演后处理
这是 Excel 工作簿，不是普通 txt 控制文件。
必须包含 control 工作表。
control 工作表第 1 行第 2 列写测点配置数量；前 n 行用于测点映射：
第 1 列：配置表名；第 3 列：测点标签；第 4 列：测点ID；第 5 列：计算结果ID；
第 6-9 列：坐标/附加坐标；第 9 列可写 node 或 ele，缺省按 node。
每个配置表名必须对应一个同名工作表；该工作表中配置计算测值工作簿、时间步映射、比例系数、输出方向等。
该格式字段较多，建议先复制已有 control.xlsx 模板再改测点、文件名和时间步。""",
}


def control_file_help_for(task: TaskSpec) -> str | None:
    return CONTROL_FILE_HELP.get(task.key)
