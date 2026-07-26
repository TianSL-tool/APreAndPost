from __future__ import annotations

from dataclasses import dataclass

from .base import BaseElement, ElementCategory, PayloadFormat


@dataclass(frozen=True, slots=True)
class HigherOrderEdge:
    """一个面内有向高阶边的端点、阶次和内部节点。"""

    start_node_id: int
    end_node_id: int
    order: int
    internal_node_ids: tuple[int, ...]

    @property
    def node_ids(self) -> tuple[int, ...]:
        return (self.start_node_id, *self.internal_node_ids, self.end_node_id)


class HigherOrder(BaseElement):
    """Payload E：面角点区 + 按边排列的内部节点区。"""

    __slots__ = (
        "n_faces",
        "face_edge_counts",
        "face_edge_orders",
        "corner_nodes",
        "edge_internal_nodes",
    )
    CATEGORY = ElementCategory.SOLID_3D
    PAYLOAD_FORMAT = PayloadFormat.E
    COMPATIBLE_TYPES = frozenset({508, 805, 807})
    is_3d_solid = True

    def __init__(
        self,
        e_id,
        t_id,
        c_id,
        m_id,
        d_id,
        f_id,
        node_ids,
        face_edge_counts,
        face_edge_orders,
    ) -> None:
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id, node_ids)
        self.face_edge_counts = tuple(int(value) for value in face_edge_counts)
        self.face_edge_orders = tuple(
            tuple(int(order) for order in orders) for orders in face_edge_orders
        )
        self.n_faces = len(self.face_edge_counts)
        self.face_count = self.n_faces

        corner_nodes: list[tuple[int, ...]] = []
        edge_internal_nodes: list[tuple[tuple[int, ...], ...]] = []
        node_offset = 0
        for edge_count, orders in zip(
            self.face_edge_counts, self.face_edge_orders
        ):
            face_node_count = edge_count + sum(order - 1 for order in orders)
            face = self.node_ids[node_offset : node_offset + face_node_count]
            corners = face[:edge_count]
            internal_flat = face[edge_count:]
            internal_offset = 0
            face_internal: list[tuple[int, ...]] = []
            for order in orders:
                internal_count = order - 1
                end = internal_offset + internal_count
                face_internal.append(internal_flat[internal_offset:end])
                internal_offset = end
            corner_nodes.append(corners)
            edge_internal_nodes.append(tuple(face_internal))
            node_offset += face_node_count

        self.corner_nodes = tuple(corner_nodes)
        self.edge_internal_nodes = tuple(edge_internal_nodes)
        self.corner_node_ids = tuple(
            dict.fromkeys(node_id for face in self.corner_nodes for node_id in face)
        )
        self.edge_node_ids = tuple(
            dict.fromkeys(
                node_id
                for face in self.edge_internal_nodes
                for edge in face
                for node_id in edge
            )
        )
        distinct_orders = {
            order for orders in self.face_edge_orders for order in orders
        }
        self.polynomial_order = (
            distinct_orders.pop() if len(distinct_orders) == 1 else None
        )

    @property
    def edges_per_face(self) -> tuple[int, ...]:
        """旧名称兼容别名。"""
        return self.face_edge_counts

    @property
    def orders_per_face(self) -> tuple[tuple[int, ...], ...]:
        """旧名称兼容别名。"""
        return self.face_edge_orders

    @property
    def nodes_per_face(self) -> tuple[int, ...]:
        return tuple(
            edge_count + sum(order - 1 for order in orders)
            for edge_count, orders in zip(
                self.face_edge_counts, self.face_edge_orders
            )
        )

    @property
    def face_nodes(self) -> tuple[tuple[int, ...], ...]:
        return tuple(
            (
                *corners,
                *(
                    node_id
                    for edge_internal in face_internal
                    for node_id in edge_internal
                ),
            )
            for corners, face_internal in zip(
                self.corner_nodes, self.edge_internal_nodes
            )
        )

    @property
    def edge_maps(self) -> tuple[tuple[HigherOrderEdge, ...], ...]:
        result: list[tuple[HigherOrderEdge, ...]] = []
        for corners, orders, face_internal in zip(
            self.corner_nodes,
            self.face_edge_orders,
            self.edge_internal_nodes,
        ):
            edge_count = len(corners)
            result.append(
                tuple(
                    HigherOrderEdge(
                        start_node_id=corners[index],
                        end_node_id=corners[(index + 1) % edge_count],
                        order=orders[index],
                        internal_node_ids=face_internal[index],
                    )
                    for index in range(edge_count)
                )
            )
        return tuple(result)

    @property
    def face_edges(self) -> tuple[tuple[tuple[int, ...], ...], ...]:
        """每条边按“起点、内部节点、终点”展开，便于几何操作。"""
        return tuple(
            tuple(edge.node_ids for edge in face_edges)
            for face_edges in self.edge_maps
        )

    def faces(self) -> tuple[tuple[int, ...], ...]:
        return self.face_nodes

    def topology_payload(self) -> tuple[int, ...]:
        return (
            self.n_faces,
            *self.face_edge_counts,
            *(
                order
                for face_orders in self.face_edge_orders
                for order in face_orders
            ),
            *(node_id for face in self.face_nodes for node_id in face),
        )

    @classmethod
    def from_topology(
        cls,
        e_id,
        t_id,
        c_id,
        m_id,
        d_id,
        f_id,
        face_edge_orders,
        corner_nodes,
        edge_internal_nodes,
    ) -> HigherOrder:
        normalized_orders = tuple(
            tuple(int(order) for order in orders) for orders in face_edge_orders
        )
        normalized_corners = tuple(
            tuple(int(node_id) for node_id in face) for face in corner_nodes
        )
        normalized_internal = tuple(
            tuple(
                tuple(int(node_id) for node_id in edge_internal)
                for edge_internal in face
            )
            for face in edge_internal_nodes
        )
        if not (
            len(normalized_orders)
            == len(normalized_corners)
            == len(normalized_internal)
        ):
            raise ValueError("HigherOrder 的阶次、角点和边内部节点面数不一致")
        if len(normalized_orders) < 4:
            raise ValueError("HigherOrder 至少需要 4 个面")
        for face_index, (orders, corners, face_internal) in enumerate(
            zip(normalized_orders, normalized_corners, normalized_internal), 1
        ):
            if len(orders) < 3 or len(corners) != len(orders):
                raise ValueError(
                    f"HigherOrder 第 {face_index} 面的边数与角点数不一致"
                )
            if len(face_internal) != len(orders):
                raise ValueError(
                    f"HigherOrder 第 {face_index} 面的边内部节点组数量错误"
                )
            for edge_index, (order, internal) in enumerate(
                zip(orders, face_internal), 1
            ):
                if order <= 0 or len(internal) != order - 1:
                    raise ValueError(
                        f"HigherOrder 第 {face_index} 面第 {edge_index} 边应有 "
                        f"{order - 1} 个内部节点，实际为 {len(internal)}"
                    )
        face_nodes = tuple(
            (
                *corners,
                *(node_id for edge in face_internal for node_id in edge),
            )
            for corners, face_internal in zip(
                normalized_corners, normalized_internal
            )
        )
        return cls(
            e_id,
            t_id,
            c_id,
            m_id,
            d_id,
            f_id,
            tuple(node_id for face in face_nodes for node_id in face),
            tuple(len(orders) for orders in normalized_orders),
            normalized_orders,
        )

    @classmethod
    def from_structure(
        cls,
        e_id,
        t_id,
        c_id,
        m_id,
        d_id,
        f_id,
        orders_per_face,
        face_nodes,
    ) -> HigherOrder:
        if len(orders_per_face) < 4 or len(face_nodes) != len(orders_per_face):
            raise ValueError("HigherOrder 的面阶数与面节点结构数量不一致")
        corner_nodes: list[tuple[int, ...]] = []
        edge_internal_nodes: list[tuple[tuple[int, ...], ...]] = []
        for face_index, (orders, nodes) in enumerate(
            zip(orders_per_face, face_nodes), 1
        ):
            edge_count = len(orders)
            expected = edge_count + sum(order - 1 for order in orders)
            if edge_count < 3 or any(order <= 0 for order in orders):
                raise ValueError(f"HigherOrder 第 {face_index} 面的边阶数无效")
            if len(nodes) != expected:
                raise ValueError(
                    f"HigherOrder 第 {face_index} 面应有 {expected} 个节点，"
                    f"实际为 {len(nodes)}"
                )
            corners = tuple(nodes[:edge_count])
            internal_flat = nodes[edge_count:]
            cursor = 0
            face_internal: list[tuple[int, ...]] = []
            for order in orders:
                end = cursor + order - 1
                face_internal.append(tuple(internal_flat[cursor:end]))
                cursor = end
            corner_nodes.append(corners)
            edge_internal_nodes.append(tuple(face_internal))
        return cls.from_topology(
            e_id,
            t_id,
            c_id,
            m_id,
            d_id,
            f_id,
            tuple(tuple(orders) for orders in orders_per_face),
            tuple(corner_nodes),
            tuple(edge_internal_nodes),
        )

    @classmethod
    def from_parsed(cls, e_id, t_id, c_id, m_id, d_id, f_id, payload):
        if not payload:
            raise ValueError(f"HigherOrder 单元 {e_id} 缺少 n_faces")
        n_faces = payload[0]
        if n_faces < 4:
            raise ValueError(f"HigherOrder 单元 {e_id} 的面数必须不少于 4")
        if len(payload) < 1 + n_faces:
            raise ValueError(
                f"HigherOrder 单元 {e_id} 的 face_edge_counts 不完整"
            )
        face_edge_counts = payload[1 : 1 + n_faces]
        if any(count < 3 for count in face_edge_counts):
            raise ValueError(f"HigherOrder 单元 {e_id} 的每面边数必须不少于 3")
        cursor = 1 + n_faces
        face_edge_orders: list[tuple[int, ...]] = []
        for edge_count in face_edge_counts:
            end = cursor + edge_count
            if end > len(payload):
                raise ValueError(
                    f"HigherOrder 单元 {e_id} 的 face_edge_orders 不完整"
                )
            orders = payload[cursor:end]
            if any(order <= 0 for order in orders):
                raise ValueError(f"HigherOrder 单元 {e_id} 的边阶次必须为正")
            face_edge_orders.append(orders)
            cursor = end
        node_ids = payload[cursor:]
        total_nodes = sum(
            edge_count + sum(order - 1 for order in orders)
            for edge_count, orders in zip(
                face_edge_counts, face_edge_orders
            )
        )
        if len(node_ids) != total_nodes:
            raise ValueError(
                f"HigherOrder 单元 {e_id} 应有 {total_nodes} 个面节点，"
                f"实际为 {len(node_ids)}"
            )
        return cls(
            e_id,
            t_id,
            c_id,
            m_id,
            d_id,
            f_id,
            node_ids,
            face_edge_counts,
            tuple(face_edge_orders),
        )
