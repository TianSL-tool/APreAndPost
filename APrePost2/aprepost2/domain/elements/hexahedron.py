from .base import ElementCategory, FlatElement, PayloadFormat, hexahedron_faces


class Hexahedron(FlatElement):
    """Payload A：八节点三维六面体实体。"""

    __slots__ = ()
    CATEGORY = ElementCategory.SOLID_3D
    PAYLOAD_FORMAT = PayloadFormat.A
    COMPATIBLE_TYPES = frozenset({5, 6, 23, 61, 500})
    FIXED_NODE_COUNT = 8
    CORNER_INDICES = tuple(range(8))
    FACE_COUNT = 6
    is_3d_solid = True
    is_hexahedron = True

    def faces(self) -> tuple[tuple[int, ...], ...]:
        return hexahedron_faces(self.structured_node_ids())

    def is_degenerate_tetrahedron(self) -> bool:
        ids = self.structured_node_ids()
        return ids[2] == ids[3] and len(set(ids[4:8])) == 1
