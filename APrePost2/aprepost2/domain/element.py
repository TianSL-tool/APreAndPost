"""单元类型体系 —— 每种 t_id 对应一个封装了拓扑、读写与类型知识的子类。

Element type hierarchy — each t_id maps to a subclass that encapsulates its own
topology knowledge, parse/write format, and type compatibility rules.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

import numpy as np


# ---------------------------------------------------------------------------
# 工具函数 / utilities
# ---------------------------------------------------------------------------

def _deduplicate_polygon(face: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    """去除多边形中的连续重复节点与首尾重复。

    Remove consecutive duplicate nodes from a polygon face, and strip the
    trailing node if it repeats the first.
    """
    result: list[int] = []
    for node_id in face:
        if not result or result[-1] != node_id:
            result.append(node_id)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    return tuple(dict.fromkeys(result))


# ---------------------------------------------------------------------------
# 抽象基类 / abstract base class
# ---------------------------------------------------------------------------

class BaseElement(ABC):
    """所有单元类型的抽象基类。

    Abstract base for all element types.  Carries the six engineering attributes
    and the node-id tuple shared by every element record.
    """

    __slots__ = (
        "e_id", "t_id", "c_id", "m_id", "d_id", "f_id",
        "node_ids", "_center",
    )

    # ---- 类型兼容表 / type compatibility ----
    COMPATIBLE_TYPES: ClassVar[frozenset[int]] = frozenset()

    def __init__(
        self,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        node_ids: tuple[int, ...],
    ) -> None:
        self.e_id = e_id
        self.t_id = t_id
        self.c_id = c_id
        self.m_id = m_id
        self.d_id = d_id
        self.f_id = f_id
        self.node_ids = node_ids
        self._center: np.ndarray | None = None

    # -- 形心（缓存）/ center (cached) ----------------------------------------

    def center(self, node_map: dict[int, Node]) -> np.ndarray:
        """基于唯一节点坐标的算术平均形心（去除重合节点后）。

        Arithmetic-mean centroid after deduplicating coincident nodes.
        """
        if self._center is None:
            unique: dict[tuple[float, float, float], None] = {}
            for node_id in self.node_ids:
                node = node_map[node_id]
                key = (round(node.x, 8), round(node.y, 8), round(node.z, 8))
                unique[key] = None
            if not unique:
                raise ValueError(f"单元 {self.e_id} 不包含节点 / has no nodes")
            self._center = np.mean(
                np.asarray(tuple(unique), dtype=np.float64), axis=0
            )
        return self._center

    def invalidate_geometry_cache(self) -> None:
        """清除形心缓存。／ Clear cached centroid."""
        self._center = None

    # -- 文件写出格式 / file-write payload ------------------------------------

    @abstractmethod
    def topology_payload(self) -> tuple[int, ...]:
        """返回写入 .dat 文件时 6 个属性之后的部分。

        Return the portion after the six engineering attributes for .dat output.
        """
        ...

    # -- 面拓扑（用于三维切割）/ face topology (3-D cutting) ------------------

    def faces(self) -> tuple[tuple[int, ...], ...]:
        """返回面节点编号元组；不支持切割的类型返回空元组。

        Return face node-id tuples; empty tuple for types that cannot be cut.
        """
        return ()

    # -- 分类属性 / category properties (override in subclasses) --------------

    @property
    def is_3d_solid(self) -> bool:
        return False

    @property
    def is_2d_solid(self) -> bool:
        return False

    @property
    def is_interface(self) -> bool:
        return False

    @property
    def is_hexahedron(self) -> bool:
        return False

    @property
    def is_polyhedron(self) -> bool:
        return False

    # -- 解析构造 / parse-time construction ----------------------------------

    @classmethod
    @abstractmethod
    def from_parsed(
        cls,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        payload: tuple[int, ...],
    ) -> BaseElement:
        """从文件解析出的属性 + payload 构造实例。

        Construct an instance from the six engineering attributes and the
        remainder of the element line.
        """
        ...


# ---------------------------------------------------------------------------
# 平面节点列表元素 ／ flat-node-list elements
# ---------------------------------------------------------------------------

class FlatElement(BaseElement, ABC):
    """以单一节点编号列表写出的单元（无面/边结构前言）。

    Element written as a flat list of node IDs, without face/edge preamble.
    """

    __slots__ = ()

    def topology_payload(self) -> tuple[int, ...]:
        return self.node_ids

    @classmethod
    def from_parsed(
        cls,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        payload: tuple[int, ...],
    ) -> FlatElement:
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, payload)


# -- 二维四边形实体 / 2-D quadrilateral solid --------------------------------

class QuadSolid2D(FlatElement):
    """二维四边形实体单元。／ 2-D quadrilateral solid element.

    t_id: 1, 2, 102, 222
    """

    __slots__ = ()

    COMPATIBLE_TYPES: ClassVar[frozenset[int]] = frozenset({1, 2, 222})
    is_2d_solid = True


# -- 二维多边形实体 / 2-D polygon solid --------------------------------------

class PolygonSolid2D(FlatElement):
    """二维多边形实体单元。／ 2-D polygon solid element.

    t_id: 44, 47, 470
    """

    __slots__ = ()

    COMPATIBLE_TYPES: ClassVar[frozenset[int]] = frozenset({44, 47, 470})
    is_2d_solid = True


# -- 三维通用实体 / generic 3-D solid ----------------------------------------

class Solid3DOther(FlatElement):
    """三维实体单元（平面节点列表，无显式面拓扑）。

    3-D solid element with flat node-list topology (no explicit face data).

    t_id: 16, 18, 20, 170, 171, 190, 191, 510, 511
    """

    __slots__ = ()

    is_3d_solid = True


# -- 二维接触面 / 2-D slip/interface -----------------------------------------

class Slip2D(FlatElement):
    """二维接触面单元。／ 2-D slip/interface element.

    t_id: 4, 700, 777
    """

    __slots__ = ()

    COMPATIBLE_TYPES: ClassVar[frozenset[int]] = frozenset({4, 700, 777})
    is_interface = True


# -- 三维接触面（平面节点列表）/ 3-D slip (flat) -----------------------------

class Slip3D(FlatElement):
    """三维接触面单元（平面节点列表）。／ 3-D slip element, flat topology.

    t_id: 21, 22
    """

    __slots__ = ()

    is_interface = True


# -- 六面体实体 / hexahedron solid -------------------------------------------

class Hexahedron(FlatElement):
    """8 节点六面体实体单元。／ 8-node hexahedron solid element.

    t_id: 5, 6, 23, 61, 500

    节点顺序：前 4 个为底面（逆时针），后 4 个为顶面（逆时针）。

    Node order: first 4 = bottom face (counter-clockwise),
    last 4 = top face (counter-clockwise).
    """

    __slots__ = ()

    COMPATIBLE_TYPES: ClassVar[frozenset[int]] = frozenset({5, 6, 23, 61, 500})
    is_3d_solid = True
    is_hexahedron = True

    def faces(self) -> tuple[tuple[int, ...], ...]:
        """6 个四边形面。／ 6 quadrilateral faces."""
        ids = self.node_ids
        if len(ids) < 8:
            raise ValueError(f"单元 {self.e_id} 的六面体节点数不足 8 / hex needs ≥8 nodes")
        raw = (
            (ids[3], ids[2], ids[1], ids[0]),   # bottom
            (ids[4], ids[5], ids[6], ids[7]),   # top
            (ids[0], ids[4], ids[7], ids[3]),   # front
            (ids[3], ids[7], ids[6], ids[2]),   # right
            (ids[2], ids[6], ids[5], ids[1]),   # back
            (ids[1], ids[5], ids[4], ids[0]),   # left
        )
        return tuple(
            cleaned for face in raw
            if len(cleaned := _deduplicate_polygon(face)) >= 3
        )


# -- 六面体接触面 / hexahedron contact interface -----------------------------

class HexContact(FlatElement):
    """8 节点六面体接触面单元。／ 8-node hexahedron contact element.

    t_id: 9, 902, 903

    面拓扑与 Hexahedron 相同；分类上同时标记为接触面和六面体。

    Face topology identical to Hexahedron; classified as both interface and hex.
    """

    __slots__ = ()

    COMPATIBLE_TYPES: ClassVar[frozenset[int]] = frozenset({9, 902, 903})
    is_interface = True
    is_hexahedron = True

    def faces(self) -> tuple[tuple[int, ...], ...]:
        """6 个四边形面。／ 6 quadrilateral faces."""
        ids = self.node_ids
        if len(ids) < 8:
            raise ValueError(
                f"单元 {self.e_id} 的六面体接触面节点数不足 8 / "
                f"hex contact needs ≥8 nodes"
            )
        raw = (
            (ids[3], ids[2], ids[1], ids[0]),
            (ids[4], ids[5], ids[6], ids[7]),
            (ids[0], ids[4], ids[7], ids[3]),
            (ids[3], ids[7], ids[6], ids[2]),
            (ids[2], ids[6], ids[5], ids[1]),
            (ids[1], ids[5], ids[4], ids[0]),
        )
        return tuple(
            cleaned for face in raw
            if len(cleaned := _deduplicate_polygon(face)) >= 3
        )


# -- 多面体实体 / polyhedron solid -------------------------------------------

class Polyhedron(BaseElement):
    """面结构化多面体单元。／ Face-structured polyhedron element.

    t_id: 53, 57, 59, 80, 800

    payload 格式：面数 + 每面节点数 + 展平节点编号。

    Payload format: face-count + per-face node-counts + flattened node IDs.
    """

    __slots__ = ("_faces",)

    COMPATIBLE_TYPES: ClassVar[frozenset[int]] = frozenset({53, 57, 59, 80, 800})
    is_3d_solid = True
    is_polyhedron = True

    def __init__(
        self,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        node_ids: tuple[int, ...],
        faces: tuple[tuple[int, ...], ...],
    ) -> None:
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id, node_ids)
        self._faces = faces

    def topology_payload(self) -> tuple[int, ...]:
        return (
            len(self._faces),
            *(len(face) for face in self._faces),
            *(node_id for face in self._faces for node_id in face),
        )

    def faces(self) -> tuple[tuple[int, ...], ...]:
        return self._faces

    @classmethod
    def from_parsed(
        cls,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        payload: tuple[int, ...],
    ) -> Polyhedron:
        if not payload:
            raise ValueError("多面体单元缺少拓扑数据 / polyhedron missing topology")
        face_count = payload[0]
        if face_count < 4 or len(payload) < 1 + face_count:
            raise ValueError(
                f"单元 {e_id} 的多面体面数量无效 / invalid face count: {face_count}"
            )
        counts = payload[1 : 1 + face_count]
        flattened = payload[1 + face_count :]
        if any(count < 3 for count in counts) or sum(counts) != len(flattened):
            raise ValueError(
                f"单元 {e_id} 的多面体面节点数量不一致 / face node counts mismatch"
            )
        faces: list[tuple[int, ...]] = []
        offset = 0
        for count in counts:
            faces.append(flattened[offset : offset + count])
            offset += count
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, flattened, tuple(faces))


# -- 多边形接触面 / polygon contact interface --------------------------------

class PolygonContact(BaseElement):
    """多边形接触面单元。／ Polygon contact interface element.

    t_id: 60, 601, 602

    node_ids = 下表面节点 + 上表面节点（长度相等）。
    node_ids = bottom-face nodes + top-face nodes (equal-length halves).
    """

    __slots__ = ()

    COMPATIBLE_TYPES: ClassVar[frozenset[int]] = frozenset({60, 601, 602})
    is_interface = True

    def topology_payload(self) -> tuple[int, ...]:
        return self.node_ids

    def faces(self) -> tuple[tuple[int, ...], ...]:
        """下表面 + 上表面 + 侧面四边形。／ Bottom + top + lateral quads."""
        ids = self.node_ids
        half = len(ids) // 2
        raw: list[tuple[int, ...]] = [
            tuple(reversed(ids[:half])),          # bottom (reversed for outward normal)
            ids[half:],                            # top
        ]
        raw.extend(
            (
                ids[index],
                ids[(index + 1) % half],
                ids[(index + 1) % half + half],
                ids[index + half],
            )
            for index in range(half)
        )
        return tuple(
            cleaned for face in raw
            if len(cleaned := _deduplicate_polygon(face)) >= 3
        )

    @classmethod
    def from_parsed(
        cls,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        payload: tuple[int, ...],
    ) -> PolygonContact:
        if len(payload) % 2:
            raise ValueError(
                f"界面单元 {e_id} 的节点数必须为偶数 / node count must be even"
            )
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, payload)


# -- 边结构化二维单元 / edge-structured 2-D element --------------------------

class EdgeStructured2D(BaseElement):
    """带边数 + 每边节点数前言的多边形二维单元。

    2-D polygon element with edge-count + per-edge-node-count preamble.

    t_id: 443, 444, 644
    """

    __slots__ = ("_edge_count", "_edge_sizes")

    COMPATIBLE_TYPES: ClassVar[frozenset[int]] = frozenset({443, 444, 644})
    is_2d_solid = True

    def __init__(
        self,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        node_ids: tuple[int, ...],
        edge_count: int,
        edge_sizes: tuple[int, ...],
    ) -> None:
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id, node_ids)
        self._edge_count = edge_count
        self._edge_sizes = edge_sizes

    def topology_payload(self) -> tuple[int, ...]:
        return (self._edge_count, *self._edge_sizes, *self.node_ids)

    @classmethod
    def from_parsed(
        cls,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        payload: tuple[int, ...],
    ) -> EdgeStructured2D:
        if not payload:
            raise ValueError("边结构化单元缺少拓扑数据 / missing edge topology")
        edge_count = payload[0]
        if edge_count < 3 or len(payload) < 1 + edge_count:
            raise ValueError(f"单元 {e_id} 的边数无效 / invalid edge count: {edge_count}")
        edge_sizes = payload[1 : 1 + edge_count]
        node_ids = payload[1 + edge_count :]
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, node_ids, edge_count, edge_sizes)


# -- 高阶多面体 / higher-order polyhedron ------------------------------------

class HigherOrder(BaseElement):
    """高阶多面体单元（带面内边阶数前言）。

    Higher-order polyhedron element with per-face edge-order preamble.

    t_id: 508, 805, 807
    """

    __slots__ = ("_face_count", "_edges_per_face", "_nodes_per_face", "_face_orders", "_faces")

    is_3d_solid = True

    def __init__(
        self,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        node_ids: tuple[int, ...],
        face_count: int,
        edges_per_face: tuple[int, ...],
        face_orders: tuple[tuple[int, ...], ...],
        faces: tuple[tuple[int, ...], ...] | None = None,
    ) -> None:
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id, node_ids)
        self._face_count = face_count
        self._edges_per_face = edges_per_face
        # 每面节点数 = 该面各边阶数之和 / nodes per face = sum of edge orders
        self._nodes_per_face: tuple[int, ...] = tuple(
            sum(orders) for orders in face_orders
        )
        self._face_orders = face_orders
        self._faces: tuple[tuple[int, ...], ...] | None = faces

    def topology_payload(self) -> tuple[int, ...]:
        orders_flat = tuple(
            order for face_orders in self._face_orders for order in face_orders
        )
        return (self._face_count, *self._edges_per_face, *orders_flat, *self.node_ids)

    def faces(self) -> tuple[tuple[int, ...], ...]:
        if self._faces is None:
            # 每面按节点数切分 node_ids / slice node_ids by nodes-per-face
            reconstructed: list[tuple[int, ...]] = []
            offset = 0
            for count in self._nodes_per_face:
                reconstructed.append(self.node_ids[offset : offset + count])
                offset += count
            self._faces = tuple(reconstructed)
        return self._faces

    @classmethod
    def from_parsed(
        cls,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        payload: tuple[int, ...],
    ) -> HigherOrder:
        if not payload:
            raise ValueError("高阶单元缺少拓扑数据 / missing higher-order topology")
        face_count = payload[0]
        if face_count < 4 or len(payload) < 1 + face_count:
            raise ValueError(
                f"单元 {e_id} 的高阶单元面数无效 / invalid face count: {face_count}"
            )
        edges_per_face = payload[1 : 1 + face_count]
        idx = 1 + face_count
        face_orders: list[tuple[int, ...]] = []
        for edge_count in edges_per_face:
            if idx + edge_count > len(payload):
                raise ValueError(
                    f"单元 {e_id} 的高阶单元边阶数数据不完整 / edge order data truncated"
                )
            face_orders.append(payload[idx : idx + edge_count])
            idx += edge_count
        node_ids = payload[idx:]
        # 每面节点数 = 该面各边阶数之和 / nodes per face = sum of edge orders
        total_nodes = sum(sum(orders) for orders in face_orders)
        if len(node_ids) != total_nodes:
            raise ValueError(
                f"单元 {e_id} 的高阶单元节点数与面阶数之和不匹配 / "
                f"node count {len(node_ids)} ≠ sum of face orders {total_nodes}"
            )
        return cls(
            e_id, t_id, c_id, m_id, d_id, f_id, node_ids,
            face_count, edges_per_face, tuple(face_orders),
        )


# -- 结构化接触面 / structured contact ---------------------------------------

class StructuredContact(BaseElement):
    """带前言元数据的接触面单元。／ Contact element with preamble metadata.

    t_id: 223 (4 元前言), 224 (3 元前言)

    preamble length: 4 for 223, 3 for 224.
    """

    __slots__ = ("_mid_info",)

    is_interface = True

    # 不同 t_id 的前言长度不同 / different preamble lengths per t_id
    _PREAMBLE_SIZE: ClassVar[dict[int, int]] = {223: 4, 224: 3}

    def __init__(
        self,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        node_ids: tuple[int, ...],
        mid_info: tuple[int, ...],
    ) -> None:
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id, node_ids)
        self._mid_info = mid_info

    def topology_payload(self) -> tuple[int, ...]:
        return (*self._mid_info, *self.node_ids)

    @classmethod
    def from_parsed(
        cls,
        e_id: int,
        t_id: int,
        c_id: int,
        m_id: int,
        d_id: int,
        f_id: int,
        payload: tuple[int, ...],
    ) -> StructuredContact:
        mid_len = cls._PREAMBLE_SIZE.get(t_id, 0)
        if len(payload) < mid_len + 1:
            raise ValueError(
                f"结构化接触面单元 {e_id} 缺少前言元数据 / "
                f"missing preamble for t_id {t_id}"
            )
        mid_info = payload[:mid_len]
        node_ids = payload[mid_len:]
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, node_ids, mid_info)


# ===========================================================================
# 类型注册表 & 工厂 / type registry & factory
# ===========================================================================

_TYPE_REGISTRY: dict[int, type[BaseElement]] = {
    # -- 二维实体 / 2-D solids --
    1:   QuadSolid2D,
    2:   QuadSolid2D,
    102: QuadSolid2D,
    222: QuadSolid2D,
    44:  PolygonSolid2D,
    47:  PolygonSolid2D,
    470: PolygonSolid2D,
    # -- 三维实体 / 3-D solids --
    5:   Hexahedron,
    6:   Hexahedron,
    23:  Hexahedron,
    61:  Hexahedron,
    500: Hexahedron,
    16:  Solid3DOther,
    18:  Solid3DOther,
    20:  Solid3DOther,
    170: Solid3DOther,
    171: Solid3DOther,
    190: Solid3DOther,
    191: Solid3DOther,
    510: Solid3DOther,
    511: Solid3DOther,
    53:  Polyhedron,
    57:  Polyhedron,
    59:  Polyhedron,
    80:  Polyhedron,
    800: Polyhedron,
    508: HigherOrder,
    805: HigherOrder,
    807: HigherOrder,
    # -- 接触面 / interfaces --
    4:   Slip2D,
    700: Slip2D,
    777: Slip2D,
    9:   HexContact,
    902: HexContact,
    903: HexContact,
    21:  Slip3D,
    22:  Slip3D,
    60:  PolygonContact,
    601: PolygonContact,
    602: PolygonContact,
    223: StructuredContact,
    224: StructuredContact,
    # -- 边结构化二维 / edge-structured 2-D --
    443: EdgeStructured2D,
    444: EdgeStructured2D,
    644: EdgeStructured2D,
}


def create_element(
    e_id: int,
    t_id: int,
    c_id: int,
    m_id: int,
    d_id: int,
    f_id: int,
    payload: tuple[int, ...],
) -> BaseElement:
    """工厂：根据 t_id 创建对应子类实例。

    Factory: create the correct element subclass from parsed data.
    """
    element_class = _TYPE_REGISTRY.get(t_id)
    if element_class is None:
        raise ValueError(f"不支持的元素类型 / unsupported element type: {t_id}")
    return element_class.from_parsed(e_id, t_id, c_id, m_id, d_id, f_id, payload)


def replace_element_type(
    element: BaseElement,
    new_t_id: int,
) -> BaseElement:
    """创建一个类型不同的新单元实例，同时校验转换的合法性。

    Create a new element instance with a different t_id, validating that the
    conversion is permitted by the source type's COMPATIBLE_TYPES.

    特殊规则 / special rule:
    - 同类型的 t_id 变换始终允许（如同为 Hexahedron 的 6→61）。
      Same-subclass t_id changes are always allowed (e.g. 6→61 within Hexahedron).
    """
    new_class = _TYPE_REGISTRY.get(new_t_id)

    # 同子类内允许 / same subclass always OK
    if new_class is not type(element):
        compatible = type(element).COMPATIBLE_TYPES
        if new_t_id not in compatible:
            raise ValueError(
                f"尚未注册安全的单元转换规则：{element.t_id} -> {new_t_id}"
            )
        if new_class is None:
            raise ValueError(
                f"不支持的目标类型 / unsupported target type: {new_t_id}"
            )

    payload = element.topology_payload()
    return new_class.from_parsed(
        element.e_id, new_t_id, element.c_id, element.m_id,
        element.d_id, element.f_id, payload,
    )


# 向后兼容别名 / backward-compatible alias
Element = BaseElement
