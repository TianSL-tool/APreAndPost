# APrePost2

APrePost 的独立重写版本。原工程保持不变，新程序不导入原工程的 Python 包。

## 设计目标

- 保持节点编号、单元编号、材料号、填筑号、边界条件和节点连接顺序。
- UI、业务服务、文件格式和领域对象相互解耦。
- 大文件采用流式读写，输出采用临时文件原子替换。
- 耗时任务在 Qt 后台线程池运行，避免界面假死。
- 三维切割、结果读取和反演后处理均由新项目内的独立服务实现。

## 运行

```powershell
cd APrePost2
python -m pip install -e .
python run.py
```

## 测试

```powershell
python -m unittest discover -s tests -v
```

## 当前功能覆盖

原主程序的 13 个菜单功能均由 `APrePost2/aprepost2/` 内的代码实现。运行时不导入
`pre_group`、`post`、`Node`、`Element` 或 `Face` 等原工程模块，也不依赖 `pyvista`。

- `services/mesh_cutting.py`：凸多面体和三维界面单元平面切割、交点合并及边界节点插入。
- `services/mesh_section.py`：按原点和法向量抽取三维实体及 9 系列接触面，分别输出二维多边形与分层二维接触单元。
- `services/result_reader.py`：HDF5 拓扑继承、节点/单元时程、应力应变派生量和分步输出。
- `services/inversion.py`：反演配置、测值/计算值插值、CAD 文本和 Excel 输出。
- `domain/element.py`：按 Payload A–G 建模的具体单元类、严格解析校验和 `t_id` 注册表；
  详细结构见 [docs/ELEMENT_MODEL.md](docs/ELEMENT_MODEL.md)。

## 控制文件兼容约定

- 材料号、填筑号、孔压材料对：首行为数量，随后每行为两个整数。
- 单元类型转换：材料数量、逐行材料号、转换对数量、逐行“旧类型 新类型”。
- 最近节点：首行为测点数，随后为 `label id x y z`。
- 最近单元：首行为测点数，随后为 `label id x y z material...`。
- 坐标缩放：继续使用 `BASE_POINT`、`SCALE_DIR`、`SCALE_RANGE_MIN`、
  `SCALE_RANGE_MAX` 和 `SCALE_FACTOR` 键值。

所有新网格修改服务禁止输入文件与输出文件相同。输出先写入同目录临时文件，成功后再原子替换。

## 尚需工程数据验证

自动测试覆盖字段保持、连接顺序、属性修改、空间检索、HDF5 合并、六面体/界面单元切割、
HDF5 时程读取和最小反演流程。仓库中仍没有真实 `Inimesh.dat`、计算结果 HDF5 或反演工作簿，
因此正式工程使用前仍须用代表性算例对节点拓扑、应力应变符号和插值结果进行对照验算。
