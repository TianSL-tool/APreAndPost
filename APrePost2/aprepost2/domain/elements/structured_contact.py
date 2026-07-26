from __future__ import annotations

from abc import ABC
from typing import ClassVar

from .base import BaseElement, ElementCategory, PayloadFormat


class StructuredContact(BaseElement, ABC):
    """Payload G：跨阶接触面的公共结构化解析。"""

    __slots__ = (
        "mid_flags",
        "bottom_corner_ids",
        "bottom_mid_ids",
        "top_corner_ids",
        "top_mid_ids",
    )
    CATEGORY = ElementCategory.CONTACT_3D
    PAYLOAD_FORMAT = PayloadFormat.G
    is_interface = True

    PREAMBLE_SIZE: ClassVar[int]
    CORNER_COUNT: ClassVar[int]

    def __init__(
        self, e_id, t_id, c_id, m_id, d_id, f_id, node_ids, mid_flags
    ) -> None:
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id, node_ids)
        self.mid_flags = tuple(int(value) for value in mid_flags)
        mid_count = sum(self.mid_flags)
        self.bottom_corner_ids = self.node_ids[: self.CORNER_COUNT]
        start = self.CORNER_COUNT
        self.bottom_mid_ids = self.node_ids[start : start + mid_count]
        start += mid_count
        self.top_corner_ids = self.node_ids[start : start + self.CORNER_COUNT]
        start += self.CORNER_COUNT
        self.top_mid_ids = self.node_ids[start:]
        self.corner_node_ids = self.bottom_corner_ids + self.top_corner_ids
        self.edge_node_ids = self.bottom_mid_ids + self.top_mid_ids
        if mid_count == 0:
            self.polynomial_order = 1
        elif mid_count == len(self.mid_flags):
            self.polynomial_order = 2
        else:
            self.polynomial_order = None

    @property
    def mid_node_count_per_side(self) -> int:
        return sum(self.mid_flags)

    def topology_payload(self) -> tuple[int, ...]:
        return (
            *self.mid_flags,
            *self.bottom_corner_ids,
            *self.bottom_mid_ids,
            *self.top_corner_ids,
            *self.top_mid_ids,
        )

    @classmethod
    def from_layers(
        cls,
        e_id,
        t_id,
        c_id,
        m_id,
        d_id,
        f_id,
        mid_flags,
        bottom_corners,
        bottom_mids,
        top_corners,
        top_mids,
    ) -> StructuredContact:
        if len(mid_flags) != cls.PREAMBLE_SIZE or any(
            flag not in (0, 1) for flag in mid_flags
        ):
            raise ValueError(f"{cls.__name__} 的中边节点标志无效")
        mid_count = sum(mid_flags)
        if (
            len(bottom_corners) != cls.CORNER_COUNT
            or len(top_corners) != cls.CORNER_COUNT
            or len(bottom_mids) != mid_count
            or len(top_mids) != mid_count
        ):
            raise ValueError(f"{cls.__name__} 的底/顶层结构与中边节点标志不一致")
        return cls(
            e_id,
            t_id,
            c_id,
            m_id,
            d_id,
            f_id,
            (*bottom_corners, *bottom_mids, *top_corners, *top_mids),
            tuple(mid_flags),
        )

    @classmethod
    def from_parsed(cls, e_id, t_id, c_id, m_id, d_id, f_id, payload):
        if len(payload) < cls.PREAMBLE_SIZE:
            raise ValueError(f"{cls.__name__} 单元 {e_id} 缺少中边节点标志")
        flags = payload[: cls.PREAMBLE_SIZE]
        if any(flag not in (0, 1) for flag in flags):
            raise ValueError(f"{cls.__name__} 单元 {e_id} 的标志只能为 0 或 1")
        node_ids = payload[cls.PREAMBLE_SIZE :]
        expected = 2 * cls.CORNER_COUNT + 2 * sum(flags)
        if len(node_ids) != expected:
            raise ValueError(
                f"{cls.__name__} 单元 {e_id} 应有 {expected} 个节点，"
                f"实际为 {len(node_ids)}"
            )
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, node_ids, flags)
