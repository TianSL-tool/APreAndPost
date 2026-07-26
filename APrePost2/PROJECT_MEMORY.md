# APrePost2 项目记忆

更新时间：2026-07-26

## 范围与入口

- APrePost2 是独立重写项目，运行时不得导入原工程的 `pre_group`、`post`、`Node`、
  `Element` 或 `Face`。
- 程序入口：`run.py` → `aprepost2/app.py`。
- 主窗口：`aprepost2/ui/main_window.py`。
- 功能注册：`aprepost2/ui/task_catalog.py`，当前覆盖 26 个主功能入口。
- 需要控制文件/控制工作簿/单元号文件的功能，其制作说明维护在
  `aprepost2/ui/task_catalog.py` 的 `CONTROL_FILE_HELP`；用户选择或打开功能时，
  `main_window.py` 会把说明打印到运行日志。

## 模块职责

- `aprepost2/domain/mesh.py`：`Node`、`Mesh`。
- `aprepost2/domain/elements/`：每种具体单元类独占一个文件；`base.py` 保存公共基类，
  `registry.py` 保存 `t_id` 注册与工厂。
- `aprepost2/domain/element.py`：兼容导出层，不再保存具体单元实现。
- `aprepost2/io/mesh_io.py`：网格流式读取、解析分派、原子写出。
- `aprepost2/services/mesh_operations.py`：网格属性修改、筛选、高阶转换和按材料单元互转。
- `aprepost2/services/mesh_cutting.py`：凸多面体及三维接触面切割。
- `aprepost2/services/mesh_section.py`：抽取三维实体与给定平面的交集，输出 `t_id=44` 二维多边形截面网格。
- `aprepost2/services/result_reader.py`：HDF5 时程读取与应力应变派生量。
- `aprepost2/services/restart_export.py`：重启动 HDF5 中指定单元的高斯点应力、应变和本构内变量导出。
- `aprepost2/services/hdf5_material_filter.py`：按单元号文件复制并筛除初始条件/重启动 HDF5 中的指定单元及对应高斯点数据。
- `aprepost2/services/inversion.py`：反演工作簿解析、插值和输出。
  兼容旧测值工作簿中 `Label` 标题/标签值位于 C:D 或 D:E 的两种布局；工作表名按
  Excel 规则做大小写不敏感匹配；control 的 F:H 仅解释为 X/Y/Z 坐标，I 列解释为
  `node/ele` 结果类型。运行结果日志逐工况报告测点组、测点数、目标时刻、步时映射和输出文件。
- `aprepost2/services/tecplot_merge.py`：Tecplot ASCII 文件发现、Zone 解析、变量体系校验和单步原子合并；
  计算步按文件内 Zone 的 1-based 顺序解释，包含跨 Zone 数据共享引用的目标 Zone 会拒绝独立提取。
- `aprepost2/ui/workers.py`：Qt 后台任务，耗时计算不得阻塞主线程。
- `aprepost2/ui/plt_merge_dialog.py`：PLT 单步合并专用界面，支持添加文件、添加多个文件夹、
  递归扫描、工况名编辑、顺序调整和复制工况；同一个只读源文件可用不同工况名重复参与合并。

## 网格与单元约束

- 节点记录共 11 列；单元公共头固定为
  `e_id, t_id, c_id, m_id, d_id, f_id`。
- `node_ids` 只存真实节点编号，不混入面数、边数、阶数或中边节点标志。
- 特殊结构必须用结构化入口构造：
  `from_edges`、`from_faces`、`from_structure`、`from_surfaces`、`from_layers`。
- 单元读取后在类内保存 `corner_node_ids`、`edge_node_ids`、`face_count`、
  `polynomial_order`；Payload C/D/E/F/G 还保存面、边、逐边阶次或底/顶层嵌套分组。
- `topology_payload()` 必须由结构化字段重新组装，写出不得退回读取时的原始扁平 Payload。
- Payload E 每面先写 `face_edge_count` 个角点，再按边顺序写各边 `p-1`
  个内部节点；类内保存 `corner_nodes`、`edge_internal_nodes` 和端点映射 `edge_maps`。
- 常规二阶转 Payload E 时，每边 `order=2`；四边形面按“4角点+4中点”写8节点，
  三角形面按“3角点+3中点”写6节点。
- 二阶二维实体单元：`11/102/103/104` 为 8 节点二阶四边形，先 4 个角点后
  4 个边节点；`121/122` 为 6 节点二阶三角形，先 3 个角点后 3 个边节点。
- `444/644` 为跨阶二维多边形，Payload D 依次为边数、逐边阶次、角点和逐边内部节点；
  例如 `4 1 2 1 2 1 2 3 4 6 8`。
- `Slip3D(t_id=22)` 的节点结构尚未明确，不推断角点、边点和阶次。
- Payload 与 `t_id` 的完整映射见 `docs/ELEMENT_MODEL.md`。
- 当前注册单元类型共 50 个 `t_id`、18 个具体类；最新 Excel 清单由
  `scripts/generate_element_excel_v2.py` 读取 `ELEMENT_TYPE_REGISTRY` 生成。
- 响应类型标识位于 `aprepost2/domain/elements/response.py`，分为单相、
  饱和多孔介质直接求解、饱和多孔介质交叉迭代；`23` 尚未配置响应类型。
- `QuadraticTriangle2D` 当前包含单相 `11` 以及 `121/122`，
  `QuadraticQuad2D` 当前包含 `102/103/104`。
- 类型转换仅允许同一具体结构类的 `COMPATIBLE_TYPES` 内转换。
- 跨拓扑单元互转入口为 `convert_element_types_by_material()`；控制格式沿用材料号
  与“旧类型 新类型”映射，当前转换能力表见 `docs/ELEMENT_CONVERSION_TABLE.md`。
  反向转换只在拓扑可唯一识别时执行，不自动猜测多边形、多面体或任意高阶结构。
- 单元互转控制文件中目标类型 `0` 仅表示 `HigherOrder(508/805/807)` 自动转常规高阶；
  程序按转换表候选顺序选择第一项，无对应常规单元时输出任意高阶结构摘要。
- 节点/单元编号整体偏移允许分别设置整数增量；节点号变化必须同步更新所有 Payload
  中的真实节点编号，不得修改面数、边数、阶次或中边节点标志。
- 以节点为中心缩放所有节点使用 `CENTER_NODE_ID` 指定中心节点，支持统一
  `SCALE_FACTOR` 或分方向 `SCALE_X/SCALE_Y/SCALE_Z`；只修改节点坐标，不改节点号、
  单元连接、材料号、填筑号或约束。
- 按距离合并节点使用 `cKDTree` 候选搜索、向量化严格距离过滤和稀疏图连通分量；
  传递近邻归入同组，保留最小节点号及其坐标，节点约束逐分量取组内最大值，并同步重建单元连接。
- 保持节点/单元编号、材料号、填筑号、约束和连接顺序，除非任务明确要求修改。

## 数值约定

- 单元形心为去除重复坐标后的节点算术平均，不是体积形心。
- 三维切割仍要求被切单元为凸多面体；凸性检查不再用同一面自身节点判定外侧，
- 三维截面抽取使用“平面原点 + 法向量”定义截面，交点按几何容差全局复用；截面单元保留来源单元编号和公共工程属性。
- 截面与相邻单元公共面重合时只输出一个多边形；新交点编号从原网格最大节点号之后顺延，原始平面节点保留编号和约束。
- 截面多边形节点从法向量正向观察按逆时针排列，退化为线或点的相切情况不输出单元。
- 当前截面抽取只处理 `polynomial_order=1` 的线性三维实体；高阶实体的曲边求交尚未线性化，程序会明确跳过而不猜测拓扑。
- 截面抽取将三维接触面 `9/902/903` 分别转换为二维接触面 `4/700/777`；节点按 `[底起, 底终, 顶终, 顶起]` 排列，顶边与底边几何方向相反。
- 四节点实体截面按响应类型转为 `1/2/222`；三节点截面也转为 `1/2/222`，Payload 写成 `[n1,n2,n3,n3]`；五节点及以上保留 `44/47/470`。
- 9 系列接触面截面以对应上下节点的中面求交，再用同一边参数分别插值上下层；避免上下表面轻微错位或近共面端点造成漏切和伪短边。
- 接触面上下表面即使坐标重合也保留不同节点编号；原始同坐标异号节点不参与新交点的空间合并。
  以兼容工程六面体常见的轻微翘曲四边形面。
- `BaseElement` 提供面节点右手定则外法向检查；切割写出前会检查 57 型多面体每个面均指向外侧。
- 三维切割默认自动执行边界协调；控制文件末尾明确写入边界模式 0 时可关闭。
- 切割交点记录所属原始边；边界协调按边索引插入交点，避免对所有新节点做全局线段搜索。
- 构造 57 型多面体前只沿同一切割面在单元面上形成的两个点拆分面片；
  切割面贯穿角点时沿真实切割线拆分，不使用任意对角线。
- 切割结果会在运行日志输出控制读取、网格读取、筛选切割、边界协调、重编号校验和写出阶段耗时。
- HDF5 原始分量保持求解器符号；派生应力应变采用压缩为正。
- 重启动 HDF5 的 `output_for_restart/<step>/element_info` 六列为单元号、单元材料类型、高斯点数、应力分量数、应变分量数、单元内变量个数；`stress`、`strain`、`constitutive_variables` 按 `element_info` 单元顺序和各单元高斯点顺序扁平存储。
- 重启动单元高斯点 Excel 导出只强制要求 `element_info`；`stress`、`strain`、`constitutive_variables` 哪个数据集存在就校验并导出哪个，缺失的数据集跳过对应分量列，不中断导出。
- 初始条件 HDF5 的 `output_for_initial_condition/<step>` 使用相同的 `element_info`
  和扁平高斯点数组约定；按单元号筛除时必须依据每个单元的高斯点数与分量数同步计算三类数组偏移。
- 工程剪应变组装张量时除以 2。
- 完整数值约定见 `docs/NUMERICAL_CONVENTIONS.md`。

## 验证

- 运行相关测试：`python -m unittest tests.<模块名> -v`。
- 全量测试：`python -m unittest discover -s tests -v`。
- 当前基线：73 项测试通过，UI 无界面启动检查通过。
- 真实工程使用前仍需核验高阶节点排序、退化规则、切割拓扑、量纲和正负号。

## 节省上下文规则

- 开始任务先读本文件，再只打开任务直接涉及的源码。
- 不重复扫描原工程；只有兼容性核对明确需要时才读取旧代码。
- 开发阶段先跑相关测试，结构性修改完成后再跑一次全量测试。
- 工具输出限制到目标函数附近，避免输出整个大型文件。
- plt_step_series_merge：逐文件编辑分组输出名和计算步；自动识别末尾下划线数字、连字符数字或直接尾随数字，文件名末尾无数字的 PLT 不计入；文件明细按分组输出名升序排列，支持整行多选移除；按数值步号合并单 Zone ASCII/TDV binary，同组格式混合时自动保留数量较多的格式并仅从任务中排除少数格式文件，数量相同则拒绝猜测，所有原文件只读；界面显示分组、步号顺序、文件数和最终文件名汇总表，并支持手动更新。
