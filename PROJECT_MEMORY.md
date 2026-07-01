# APrePost 项目架构记忆

更新时间：2026-07-01

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
