# APrePost 项目架构记忆

更新时间：2026-07-08

## 稳定入口

- 应用入口：`APyPreAndPost.py`
- 主窗口业务接线：`mainwindow/ui_mainwindow.py` 中的 `MainWindow`
- 主窗口界面类：`mainwindow/mainwindow.py`（由 Qt UI 生成）
- Qt Designer 源文件：`mainwindow/mainwindow.ui`

## 核心模块

- `pre_group/pre.py`：网格读取、写出、检索、切割及前处理公共逻辑。
- `Node/node.py`：节点对象；坐标、位移/孔压/转动约束及后处理结果。
- `Element/BaseElement.py`：单元抽象基类；公共编号、类型、材料、填筑属性及形心。
- `Element/ElementFactory.py`：依据 `t_id` 创建具体单元。
- `Element/SolidElement/`、`Element/SlipElement/`：实体单元和接触面单元实现。
- `post/`：HDF5 读取、结果导出、反演后处理和 HDF5 合并。

## 网格格式与关键约束

- 网格文件分为 `node ... end node` 与 `element ... end element` 两段。
- 节点记录：`node_id, x, y, z, ux, uy, uz, press, rx, ry, rz`。
- 单元公共字段：`e_id, t_id, c_id, m_id, d_id, f_id`，之后为节点编号。
- `Element.center` 是去除重复坐标节点后的算术平均形心，并带缓存。
- 只读筛选/导出不得修改对象的编号、类型、材料号、填筑号、节点连接顺序、节点坐标或约束。

## 菜单命令接入方式

1. 在 `mainwindow/mainwindow.py` 创建 `QAction`，加入“前处理”或“后处理”菜单并设置文字。
2. 在 `mainwindow/ui_mainwindow.py` 导入对话框、连接 `triggered` 信号并实现打开方法。
3. 同步更新 `mainwindow/mainwindow.ui`，防止以后重新生成界面时丢失命令。

## 当前新增功能

- `pre_group/ui_export_elements_by_range.py`：按闭区间形心范围筛选单元，并原设置写出单元及其引用节点。
- `pre_group/export_elements_by_range_dialog.py`：上述功能的输入/输出文件与六个范围值对话框。
- “前处理 → 按范围输出单元”：动作名 `actionExportElementsByRange`，按单元形心筛选。
- 安全约束：禁止输入、输出为同一文件；已有输出需确认；先写临时文件再原子替换。

## 维护规则

- 每次结构性增删改后更新本文件的对应条目和更新时间。
- 只记录已经验证的架构事实；不要记录临时调试信息、完整源码或大段日志。

## APrePost2 独立重写

- 处理 APrePost2 任务时，先读取 `APrePost2/PROJECT_MEMORY.md`，避免重复扫描新工程。
- 新程序位于 `APrePost2/`，原程序目录和入口保持不变。
- 新入口：`APrePost2/run.py`；主窗口：`APrePost2/aprepost2/ui/main_window.py`。
- `APrePost2/aprepost2/domain/`：轻量节点、单元和网格领域对象。
- `APrePost2/aprepost2/domain/element.py`：Payload A–G 单元类型体系；每个 `t_id`
  映射到具体类，由类自身负责节点数、前言、面拓扑、退化签名和类内兼容转换。
- 单元公共记录头固定为 `e_id, t_id, c_id, m_id, d_id, f_id`；`node_ids`
  仅保存真实节点编号，不包含面数、边数、阶数或中边节点标志。
- `APrePost2/aprepost2/io/`：网格与控制文本的流式读取、校验和原子写出。
- `APrePost2/aprepost2/services/`：全部前后处理用例；UI 不直接实现计算。
- `APrePost2/aprepost2/ui/`：任务目录、参数对话框和 Qt 后台任务。
- 新主窗口覆盖原主窗口 13 个功能入口。
- 13 个功能均由 `APrePost2` 内部实现；运行时不导入旧工程的
  `pre_group`、`post`、`Node`、`Element` 或 `Face` 包。
- `services/mesh_cutting.py` 独立实现凸多面体/界面单元切割、交点去重和边界协调。
- `services/result_reader.py` 独立实现 HDF5 时程提取、派生量计算和结果输出。
- `services/inversion.py` 独立实现反演工作簿解析、时间插值、CAD 文本和 Excel 输出。
- `services/legacy.py` 仅保留早期 APrePost2 函数名别名，不访问旧工程。
- 新实现的只读筛选和属性修改继续保持节点/单元编号、非目标属性及节点连接顺序。

## 2026-07-08 更新

- 新增“前处理 -> 以节点为中心缩放所有节点”：动作名 `actionScaleAllNodesByCenterNode`。
- 功能模块：`pre_group/ui_scale_all_nodes_by_center_node.py`；控制文件支持 `CENTER_NODE_ID` 与统一 `SCALE_FACTOR`，也支持 `SCALE_X`、`SCALE_Y`、`SCALE_Z` 分方向缩放。
- 缩放公式：`x' = x_c + (x - x_c) * scale_x`，`y' = y_c + (y - y_c) * scale_y`，`z' = z_c + (z - z_c) * scale_z`；仅修改节点坐标，保持节点号、单元连接、材料号、填筑号和约束不变。
- 安全约束：禁止输入网格与输出网格同名；若输出文件已存在，界面执行时必须确认覆盖。
