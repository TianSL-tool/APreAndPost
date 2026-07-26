from __future__ import annotations

from .base import BaseElement, ElementCategory, PayloadFormat, deduplicate_polygon


class PolygonContact(BaseElement):
    """Payload F：仅含角点的多边形接触面。"""

    __slots__ = ("bottom_node_ids", "top_node_ids")
    CATEGORY = ElementCategory.CONTACT_3D
    PAYLOAD_FORMAT = PayloadFormat.F
    COMPATIBLE_TYPES = frozenset({60, 601, 602})
    is_interface = True

    def __init__(
        self, e_id, t_id, c_id, m_id, d_id, f_id, node_ids
    ) -> None:
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id, node_ids)
        half = len(self.node_ids) // 2
        self.bottom_node_ids = self.node_ids[:half]
        self.top_node_ids = self.node_ids[half:]
        self.corner_node_ids = self.node_ids
        self.face_count = half + 2

    def topology_payload(self) -> tuple[int, ...]:
        return self.bottom_node_ids + self.top_node_ids

    @property
    def nodes_per_surface(self) -> int:
        return len(self.bottom_node_ids)

    @classmethod
    def from_surfaces(
        cls, e_id, t_id, c_id, m_id, d_id, f_id, bottom, top
    ) -> PolygonContact:
        if len(bottom) < 3 or len(bottom) != len(top):
            raise ValueError(
                "PolygonContact 的底面与顶面必须具有相同且不少于 3 个角点"
            )
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, tuple(bottom) + tuple(top))

    def faces(self) -> tuple[tuple[int, ...], ...]:
        bottom = self.bottom_node_ids
        top = self.top_node_ids
        count = len(bottom)
        raw: list[tuple[int, ...]] = [tuple(reversed(bottom)), top]
        raw.extend(
            (
                bottom[index],
                bottom[(index + 1) % count],
                top[(index + 1) % count],
                top[index],
            )
            for index in range(count)
        )
        return tuple(
            cleaned
            for face in raw
            if len(cleaned := deduplicate_polygon(face)) >= 3
        )

    @classmethod
    def from_parsed(cls, e_id, t_id, c_id, m_id, d_id, f_id, payload):
        if len(payload) < 6 or len(payload) % 2:
            raise ValueError(
                f"PolygonContact 单元 {e_id} 必须包含不少于 6 个偶数角点，"
                f"实际为 {len(payload)}"
            )
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, payload)
