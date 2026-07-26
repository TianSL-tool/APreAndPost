from .base import ElementCategory, FlatElement, PayloadFormat, hexahedron_faces


class HexContact(FlatElement):
    """Payload A：八节点三维六面体接触面。"""

    __slots__ = ()
    CATEGORY = ElementCategory.CONTACT_3D
    PAYLOAD_FORMAT = PayloadFormat.A
    COMPATIBLE_TYPES = frozenset({9, 902, 903})
    FIXED_NODE_COUNT = 8
    CORNER_INDICES = tuple(range(8))
    FACE_COUNT = 6
    is_interface = True
    is_hexahedron = True

    def faces(self) -> tuple[tuple[int, ...], ...]:
        return hexahedron_faces(self.structured_node_ids())

    def is_degenerate_wedge(self) -> bool:
        node_ids = self.structured_node_ids()
        return node_ids[1] == node_ids[2]
