from __future__ import annotations

from .base import BaseElement, ElementCategory, PayloadFormat


class Polyhedron(BaseElement):
    """Payload C：显式面结构多面体。"""

    __slots__ = ("_faces",)
    CATEGORY = ElementCategory.SOLID_3D
    PAYLOAD_FORMAT = PayloadFormat.C
    COMPATIBLE_TYPES = frozenset({53, 57, 59, 80, 800})
    is_3d_solid = True
    is_polyhedron = True

    def __init__(
        self, e_id, t_id, c_id, m_id, d_id, f_id, node_ids, faces
    ) -> None:
        super().__init__(e_id, t_id, c_id, m_id, d_id, f_id, node_ids)
        self._faces = tuple(tuple(face) for face in faces)
        self.corner_node_ids = tuple(dict.fromkeys(self.node_ids))
        self.face_count = len(self._faces)

    def faces(self) -> tuple[tuple[int, ...], ...]:
        return self._faces

    @property
    def face_node_groups(self) -> tuple[tuple[int, ...], ...]:
        return self._faces

    def topology_payload(self) -> tuple[int, ...]:
        return (
            len(self._faces),
            *(len(face) for face in self._faces),
            *(node_id for face in self._faces for node_id in face),
        )

    @classmethod
    def from_faces(
        cls, e_id, t_id, c_id, m_id, d_id, f_id, faces
    ) -> Polyhedron:
        if len(faces) < 4 or any(len(face) < 3 for face in faces):
            raise ValueError("Polyhedron 至少需要 4 个面，且每面至少 3 个节点")
        normalized = tuple(tuple(int(node_id) for node_id in face) for face in faces)
        return cls(
            e_id,
            t_id,
            c_id,
            m_id,
            d_id,
            f_id,
            tuple(node_id for face in normalized for node_id in face),
            normalized,
        )

    @classmethod
    def from_parsed(cls, e_id, t_id, c_id, m_id, d_id, f_id, payload):
        if not payload:
            raise ValueError(f"Polyhedron 单元 {e_id} 缺少 face_count")
        face_count = payload[0]
        if face_count < 4:
            raise ValueError(f"Polyhedron 单元 {e_id} 的面数必须不少于 4")
        if len(payload) < 1 + face_count:
            raise ValueError(f"Polyhedron 单元 {e_id} 的 face_sizes 不完整")
        face_sizes = payload[1 : 1 + face_count]
        if any(size < 3 for size in face_sizes):
            raise ValueError(f"Polyhedron 单元 {e_id} 的每个面至少需要 3 个节点")
        flattened = payload[1 + face_count :]
        if sum(face_sizes) != len(flattened):
            raise ValueError(
                f"Polyhedron 单元 {e_id} 声明 {sum(face_sizes)} 个面节点，"
                f"实际为 {len(flattened)}"
            )
        faces: list[tuple[int, ...]] = []
        offset = 0
        for size in face_sizes:
            faces.append(flattened[offset : offset + size])
            offset += size
        return cls(e_id, t_id, c_id, m_id, d_id, f_id, flattened, tuple(faces))
