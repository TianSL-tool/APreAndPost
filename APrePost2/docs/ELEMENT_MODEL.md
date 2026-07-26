# 单元结构模型

## 文件组织

具体单元类位于 `aprepost2/domain/elements/`，每种具体单元独占一个 Python 文件。
公共基类和 Payload 枚举位于 `elements/base.py`，`t_id` 注册及工厂位于
`elements/registry.py`。原 `aprepost2/domain/element.py` 仅作为兼容导出层，
已有导入路径无需修改。

网格单元记录统一由 6 个公共整数属性和一种拓扑 Payload 组成：

```text
e_id t_id c_id m_id d_id f_id <payload...>
```

公共属性不因具体单元类型而省略。`node_ids` 只保存真实节点编号，不混入面数、边数、
阶数或中边节点标志。

## 类内结构化状态

读取并不是只把 Payload 存为一串节点。每个单元对象同时保存可直接用于拓扑操作的语义信息：

- `corner_node_ids`：按该单元约定排序的角点；
- `edge_node_ids`：按该单元约定排序的中边节点；一阶单元为空；
- `face_count`：已知的几何面数量；不适用时为 0；
- `polynomial_order`：统一阶次为 1 或 2；跨阶或格式未明确时为 `None`；
- Payload D 保存 `edge_node_groups`、`edge_sizes` 和可选的 `edge_orders`；443 使用每边节点数，444/644 使用每边阶次；
- Payload C 保存 `face_node_groups`；
- Payload E 保存 `n_faces`、`face_edge_counts`、`face_edge_orders`、
  `face_nodes`、`corner_nodes`、`edge_internal_nodes` 和 `edge_maps`；
- Payload F 保存 `bottom_node_ids`、`top_node_ids`；
- Payload G 保存 `mid_flags`、底/顶角点以及底/顶中边节点。

`topology_payload()` 从上述结构字段重新组装输出，而不是直接回写最初读取的扁平
Payload。因此通过结构字段调整节点后，`write_mesh()` 输出会采用调整后的结构顺序。
对于结构尚未明确的 `Slip3D(t_id=22)`，只保留原始平面节点列表，不猜测角点、边点或阶次。

## Payload 契约

| Payload | 结构 | 解析规则 |
|---|---|---|
| A | 固定长度平面节点列表 | 节点数必须与具体类声明完全一致 |
| B | 可变长度平面节点列表 | 无前言，具体类负责最小长度或奇偶性校验 |
| C | 面结构化多面体 | `face_count, face_sizes..., face_nodes...` |
| D | 边结构化二维单元 | 443：`edge_count, edge_sizes..., edge_nodes...`；444/644：`edge_count, edge_orders..., corners..., edge_internal_nodes...` |
| E | 高阶多面体 | `n_faces, face_edge_counts..., face_edge_orders..., face_nodes...`；每面先存全部角点，再按边存 `p-1` 个内部节点 |
| F | 多边形接触面 | 偶数个角点；前半为底面、后半为顶面 |
| G | 跨阶接触面 | 3 或 4 个 0/1 标志，随后为压缩排列的底/顶角点和可选中边节点 |

## 类型注册

| 类 | t_id | Payload | 节点约束 |
|---|---|---|---|
| `QuadSolid2D` | 1, 2, 222 | A | 4 |
| `QuadraticQuad2D` | 102, 103, 104 | A | 8；先 4 个角点，后 4 个边节点 |
| `QuadraticTriangle2D` | 11, 121, 122 | A | 6；先 3 个角点，后 3 个边节点 |
| `PolygonSolid2D` | 44, 47, 470 | B | ≥3 |
| `EdgeStructured2D` | 443, 444, 644 | D | 443 为 `sum(edge_sizes)`；444/644 为 `edge_count + sum(edge_orders - 1)` |
| `Hexahedron` | 5, 6, 23, 61, 500 | A | 8 |
| `HigherOrderHexahedron` | 16, 510, 511 | A | 20 |
| `HigherOrderWedge` | 18, 170, 171 | A | 15，竖边中点先于顶边中点 |
| `HigherOrderWedgeAlt` | 20, 190, 191 | A | 15，顶边中点先于竖边中点 |
| `Polyhedron` | 53, 57, 59, 80, 800 | C | ≥4 个面，每面 ≥3 节点 |
| `HigherOrder` | 508, 805, 807 | E | 每面节点数为该面各边阶数之和 |
| `Slip2D` | 4, 700, 777 | A | 4 |
| `HexContact` | 9, 902, 903 | A | 8 |
| `Slip3D` | 22 | B | 非空 |
| `HigherOrderSlip3D` | 21 | A | 16 |
| `PolygonContact` | 60, 601, 602 | F | 偶数且 ≥6 |
| `QuadStructuredContact` | 223 | G | `8 + 2*sum(flags)` |
| `TriStructuredContact` | 224 | G | `6 + 2*sum(flags)` |

## 面与退化

- `Hexahedron`、`HexContact` 和 `PolygonContact` 根据节点排序生成切割所需的外表面。
- `Polyhedron.faces()` 原样返回文件存储的面。
- `HigherOrder.faces()` 返回每面的 `角点区 + 逐边内部节点区`。
- `Hexahedron` 的四面体退化签名为 `n3==n4` 且 `n5==n6==n7==n8`。
- `HexContact` 的三棱柱退化签名为 `n2==n3`。
- 二阶六面体表述中的退化规则与“13 个唯一节点”存在不一致，因此分别暴露：
  `has_pyramid_degeneracy_signature()` 与 `unique_node_count`，不隐式修改节点。

任何类型转换只能发生在同一具体类的 `COMPATIBLE_TYPES` 内。跨拓扑转换必须由专门算法
显式重建 Payload，禁止仅修改 `t_id`。

## 响应类型标识

`elements/response.py` 维护 `t_id` 到响应类型的映射：

- `SINGLE_PHASE`：单相；
- `SATURATED_POROUS_DIRECT`：饱和多孔介质直接求解；
- `SATURATED_POROUS_STAGGERED`：饱和多孔介质交叉迭代。

可通过 `element_response_type(t_id)` 和 `element_response_label(t_id)` 查询响应类型。
同一具体拓扑类内按响应类型查候选转换目标时，使用
`compatible_t_ids_for_response(source_t_id, target_response)`。若同一响应有多个候选，
例如 `Hexahedron` 的单相 `6` 与 `61`，调用方必须根据业务规则选择具体目标。
`23` 当前未在对比表中给出响应类型，程序不会为其推断响应标识。

## 结构化构造

业务服务不得手工拼接特殊 Payload。应使用以下入口：

- `EdgeStructured2D.from_edges(...)`
- `Polyhedron.from_faces(...)`
- `HigherOrder.from_structure(...)`
- `PolygonContact.from_surfaces(...)`
- `QuadStructuredContact.from_layers(...)`
- `TriStructuredContact.from_layers(...)`

这些入口先校验嵌套结构，再由单元类统一展平为文件 Payload。读取时执行相反过程，因此
`读取 → 结构对象 → 写出 → 再读取` 会保持边、面、阶数和底/顶层分组，而不仅保持节点总数。

## 常规二阶转 Payload E

`convert_to_higher_order()` 将 20 节点六面体和两种 15 节点三棱柱转换为
`HigherOrder`，但不创建更高阶新节点。Payload E 中的逐边整数是 polynomial order
（多项式阶数）。对于每个面，先连续写入全部角点，再按边顺序连续写入内部节点：

- 二阶边写为 `order=2`；
- 每条边在角点区由相邻两个角点确定端点，在内部节点区写入 1 个中点；
- 四边形面为 4 条二阶边，共 8 个面节点；
- 三角形面为 3 条二阶边，共 6 个面节点；
- 六面体面顺序及节点排列按 508 标准样例固定；
- 三棱柱面顺序为三个四边形侧面、底面三角形、顶面三角形。

转换后的 `corner_node_ids` 与 `edge_node_ids` 必须互不重叠；类型映射为：
`16/18/20→508`、`510/170/190→805`、`511/171/191→807`。
