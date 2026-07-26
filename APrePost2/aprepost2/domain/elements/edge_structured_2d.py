from __future__ import annotations

from .base import BaseElement, ElementCategory, PayloadFormat


class EdgeStructured2D(BaseElement):
    """Payload D：按边保存节点的二维实体。"""

    __slots__ = ("edge_sizes", "edge_orders", "_edges", "_corner_count")
    CATEGORY = ElementCategory.SOLID_2D
    PAYLOAD_FORMAT = PayloadFormat.D
    COMPATIBLE_TYPES = frozenset({443, 444, 644})
    is_2d_solid = True

    def __init__(
        self, e_id, t_id, c_id, m_id, d_id, f_id, node_ids, edge_sizes, edge_orders=None
    ) -> None:
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id, node_ids)
        self.edge_sizes = tuple(int(value) for value in edge_sizes)
        self.edge_orders = (
            tuple(int(value) for value in edge_orders)
            if edge_orders is not None
            else tuple(max(1, int(value) - 1) for value in edge_sizes)
        )
        self._corner_count = len(self.edge_sizes)
        if self.t_id in {444, 644}:
            self._edges = self._build_cross_order_edges()
            self.corner_node_ids = self.node_ids[: self._corner_count]
        else:
            self._edges = self._build_legacy_edges()
            self.corner_node_ids = tuple(edge[0] for edge in self._edges)
        self.edge_node_ids = tuple(
            node_id for edge in self._edges for node_id in edge[1:-1]
        )
        self.polynomial_order = None

    def _build_legacy_edges(self) -> tuple[tuple[int, ...], ...]:
        edges: list[tuple[int, ...]] = []
        offset = 0
        for size in self.edge_sizes:
            edges.append(self.node_ids[offset : offset + size])
            offset += size
        return tuple(edges)

    def _build_cross_order_edges(self) -> tuple[tuple[int, ...], ...]:
        corners = self.node_ids[: self._corner_count]
        internal_nodes = self.node_ids[self._corner_count :]
        edges: list[tuple[int, ...]] = []
        offset = 0
        for index, order in enumerate(self.edge_orders):
            internal_count = order - 1
            edges.append(
                (
                    corners[index],
                    *internal_nodes[offset : offset + internal_count],
                    corners[(index + 1) % self._corner_count],
                )
            )
            offset += internal_count
        return tuple(edges)

    @property
    def edge_count(self) -> int:
        return len(self._edges)

    @property
    def edge_node_groups(self) -> tuple[tuple[int, ...], ...]:
        return self._edges

    def edges(self) -> tuple[tuple[int, ...], ...]:
        return self._edges

    def topology_payload(self) -> tuple[int, ...]:
        if self.t_id in {444, 644}:
            return (
                self.edge_count,
                *self.edge_orders,
                *self.corner_node_ids,
                *self.edge_node_ids,
            )
        return (
            self.edge_count,
            *(len(edge) for edge in self._edges),
            *(node_id for edge in self._edges for node_id in edge),
        )

    @classmethod
    def from_edges(
        cls, e_id, t_id, c_id, m_id, d_id, f_id, edges
    ) -> EdgeStructured2D:
        if len(edges) < 3 or any(not edge for edge in edges):
            raise ValueError("EdgeStructured2D 至少需要 3 条非空边")
        normalized = tuple(tuple(int(node_id) for node_id in edge) for edge in edges)
        return cls(
            e_id,
            t_id,
            c_id,
            m_id,
            d_id,
            f_id,
            tuple(node_id for edge in normalized for node_id in edge),
            tuple(len(edge) for edge in normalized),
        )

    @classmethod
    def from_parsed(cls, e_id, t_id, c_id, m_id, d_id, f_id, payload):
        if not payload:
            raise ValueError(f"EdgeStructured2D 单元 {e_id} 缺少 edge_count")
        edge_count = payload[0]
        if edge_count < 3:
            raise ValueError(f"EdgeStructured2D 单元 {e_id} 的边数必须不少于 3")
        if len(payload) < 1 + edge_count:
            raise ValueError(f"EdgeStructured2D 单元 {e_id} 的 edge_sizes 不完整")
        edge_sizes = payload[1 : 1 + edge_count]
        if any(size <= 0 for size in edge_sizes):
            raise ValueError(f"EdgeStructured2D 单元 {e_id} 的每边节点数必须为正")
        node_ids = payload[1 + edge_count :]
        if int(t_id) in {444, 644}:
            edge_orders = tuple(int(value) for value in edge_sizes)
            internal_count = sum(order - 1 for order in edge_orders)
            expected_node_count = edge_count + internal_count
            if expected_node_count != len(node_ids):
                raise ValueError(
                    f"EdgeStructured2D 单元 {e_id} 声明 {edge_count} 个角点和 "
                    f"{internal_count} 个边节点，实际为 {len(node_ids)} 个节点"
                )
            return cls(
                e_id,
                t_id,
                c_id,
                m_id,
                d_id,
                f_id,
                node_ids,
                tuple(order + 1 for order in edge_orders),
                edge_orders,
            )
        if sum(edge_sizes) != len(node_ids):
            raise ValueError(
                f"EdgeStructured2D 单元 {e_id} 声明 {sum(edge_sizes)} 个节点，"
                f"实际为 {len(node_ids)}"
            )
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, node_ids, edge_sizes)
