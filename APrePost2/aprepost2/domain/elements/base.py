"""单元公共基类、Payload 枚举及拓扑辅助函数。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import TYPE_CHECKING, ClassVar

import numpy as np

if TYPE_CHECKING:
    from aprepost2.domain.mesh import Node


class ElementCategory(str, Enum):
    SOLID_2D = "二维实体"
    SOLID_3D = "三维实体"
    CONTACT_2D = "二维接触面"
    CONTACT_3D = "三维接触面"


class PayloadFormat(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"
    G = "G"


def deduplicate_polygon(face: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    consecutive: list[int] = []
    for node_id in face:
        if not consecutive or consecutive[-1] != node_id:
            consecutive.append(int(node_id))
    if len(consecutive) > 1 and consecutive[0] == consecutive[-1]:
        consecutive.pop()
    return tuple(dict.fromkeys(consecutive))


def require_exact_node_count(
    class_name: str, e_id: int, payload: tuple[int, ...], expected: int
) -> None:
    if len(payload) != expected:
        raise ValueError(
            f"{class_name} 单元 {e_id} 必须有 {expected} 个节点，实际为 {len(payload)}"
        )


def hexahedron_faces(node_ids: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
    require_exact_node_count("Hexahedron", -1, node_ids, 8)
    raw = (
        (node_ids[3], node_ids[2], node_ids[1], node_ids[0]),
        (node_ids[4], node_ids[5], node_ids[6], node_ids[7]),
        (node_ids[0], node_ids[4], node_ids[7], node_ids[3]),
        (node_ids[3], node_ids[7], node_ids[6], node_ids[2]),
        (node_ids[2], node_ids[6], node_ids[5], node_ids[1]),
        (node_ids[1], node_ids[5], node_ids[4], node_ids[0]),
    )
    return tuple(
        cleaned
        for face in raw
        if len(cleaned := deduplicate_polygon(face)) >= 3
    )


class BaseElement(ABC):
    """所有单元共享的工程属性、结构化拓扑信息与几何缓存。"""

    __slots__ = (
        "e_id",
        "t_id",
        "c_id",
        "m_id",
        "d_id",
        "f_id",
        "node_ids",
        "corner_node_ids",
        "edge_node_ids",
        "face_count",
        "polynomial_order",
        "_center",
    )

    CATEGORY: ClassVar[ElementCategory]
    PAYLOAD_FORMAT: ClassVar[PayloadFormat]
    COMPATIBLE_TYPES: ClassVar[frozenset[int]] = frozenset()
    CORNER_INDICES: ClassVar[tuple[int, ...] | None] = None
    EDGE_NODE_INDICES: ClassVar[tuple[int, ...]] = ()
    FACE_COUNT: ClassVar[int] = 0
    POLYNOMIAL_ORDER: ClassVar[int | None] = 1

    is_2d_solid: ClassVar[bool] = False
    is_3d_solid: ClassVar[bool] = False
    is_interface: ClassVar[bool] = False
    is_hexahedron: ClassVar[bool] = False
    is_polyhedron: ClassVar[bool] = False

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
        if t_id not in self.COMPATIBLE_TYPES:
            raise ValueError(
                f"{type(self).__name__} 不支持 t_id={t_id}，"
                f"允许值为 {sorted(self.COMPATIBLE_TYPES)}"
            )
        self.e_id = int(e_id)
        self.t_id = int(t_id)
        self.c_id = int(c_id)
        self.m_id = int(m_id)
        self.d_id = int(d_id)
        self.f_id = int(f_id)
        self.node_ids = tuple(int(value) for value in node_ids)
        self.corner_node_ids = (
            self.node_ids
            if self.CORNER_INDICES is None
            else tuple(self.node_ids[index] for index in self.CORNER_INDICES)
        )
        self.edge_node_ids = tuple(
            self.node_ids[index] for index in self.EDGE_NODE_INDICES
        )
        self.face_count = int(self.FACE_COUNT)
        self.polynomial_order = self.POLYNOMIAL_ORDER
        self._center: np.ndarray | None = None

    @property
    def unique_node_ids(self) -> tuple[int, ...]:
        return tuple(dict.fromkeys(self.node_ids))

    @property
    def unique_node_count(self) -> int:
        return len(self.unique_node_ids)

    def center(self, node_map: dict[int, Node]) -> np.ndarray:
        if self._center is None:
            unique_coordinates: dict[tuple[float, float, float], None] = {}
            for node_id in self.node_ids:
                node = node_map[node_id]
                unique_coordinates[
                    (round(node.x, 8), round(node.y, 8), round(node.z, 8))
                ] = None
            if not unique_coordinates:
                raise ValueError(f"单元 {self.e_id} 不包含节点")
            self._center = np.mean(
                np.asarray(tuple(unique_coordinates), dtype=np.float64), axis=0
            )
        return self._center

    def invalidate_geometry_cache(self) -> None:
        self._center = None

    def faces(self) -> tuple[tuple[int, ...], ...]:
        return ()

    def face_orientation_violations(
        self,
        node_map: dict[int, Node],
        tolerance: float = 1.0e-10,
    ) -> tuple[tuple[int, str], ...]:
        """Return faces whose node order does not produce outward normals."""
        faces = self.faces()
        if not faces:
            return ()
        element_center = self.center(node_map)
        violations: list[tuple[int, str]] = []
        for face_index, face in enumerate(faces, 1):
            points = np.asarray([node_map[node_id].coordinates for node_id in face])
            normal = np.zeros(3)
            for index, point in enumerate(points):
                normal += np.cross(point, points[(index + 1) % len(points)])
            norm = float(np.linalg.norm(normal))
            if norm <= tolerance:
                violations.append((face_index, "退化面"))
                continue
            face_center = np.mean(points, axis=0)
            outward = float(np.dot(normal, face_center - element_center))
            if outward < -tolerance:
                violations.append((face_index, f"法向指向内侧，投影值 {outward:.6g}"))
        return tuple(violations)

    def faces_are_oriented_outward(
        self,
        node_map: dict[int, Node],
        tolerance: float = 1.0e-10,
    ) -> bool:
        return not self.face_orientation_violations(node_map, tolerance)

    @abstractmethod
    def topology_payload(self) -> tuple[int, ...]:
        """返回六个公共属性之后的完整 Payload。"""

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
        """从文件 Payload 构造并校验单元。"""


class FlatElement(BaseElement, ABC):
    """Payload A/B：无前言的节点编号列表。"""

    __slots__ = ()
    FIXED_NODE_COUNT: ClassVar[int | None] = None
    MIN_NODE_COUNT: ClassVar[int] = 1

    def structured_node_ids(self) -> tuple[int, ...]:
        if self.CORNER_INDICES is None:
            return self.corner_node_ids
        classified = self.CORNER_INDICES + self.EDGE_NODE_INDICES
        if len(classified) != len(self.node_ids) or set(classified) != set(
            range(len(self.node_ids))
        ):
            return self.node_ids
        if len(self.corner_node_ids) != len(self.CORNER_INDICES):
            raise ValueError(f"{type(self).__name__} 的角点数量与结构声明不一致")
        if len(self.edge_node_ids) != len(self.EDGE_NODE_INDICES):
            raise ValueError(f"{type(self).__name__} 的边点数量与结构声明不一致")
        rebuilt = [0] * len(self.node_ids)
        for index, node_id in zip(self.CORNER_INDICES, self.corner_node_ids):
            rebuilt[index] = int(node_id)
        for index, node_id in zip(self.EDGE_NODE_INDICES, self.edge_node_ids):
            rebuilt[index] = int(node_id)
        return tuple(rebuilt)

    def topology_payload(self) -> tuple[int, ...]:
        return self.structured_node_ids()

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
        if cls.FIXED_NODE_COUNT is not None:
            require_exact_node_count(cls.__name__, e_id, payload, cls.FIXED_NODE_COUNT)
        elif len(payload) < cls.MIN_NODE_COUNT:
            raise ValueError(
                f"{cls.__name__} 单元 {e_id} 至少需要 {cls.MIN_NODE_COUNT} 个节点，"
                f"实际为 {len(payload)}"
            )
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, payload)
