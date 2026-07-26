from .base import ElementCategory, FlatElement, PayloadFormat


class HigherOrderHexahedron(FlatElement):
    """Payload A：20 节点二阶六面体。"""

    __slots__ = ()
    CATEGORY = ElementCategory.SOLID_3D
    PAYLOAD_FORMAT = PayloadFormat.A
    COMPATIBLE_TYPES = frozenset({16, 510, 511})
    FIXED_NODE_COUNT = 20
    CORNER_INDICES = tuple(range(8))
    EDGE_NODE_INDICES = tuple(range(8, 20))
    FACE_COUNT = 6
    POLYNOMIAL_ORDER = 2
    is_3d_solid = True

    def has_pyramid_degeneracy_signature(self) -> bool:
        ids = self.structured_node_ids()
        return len(set(ids[4:8])) == 1 and len(set(ids[12:16])) == 1

    @property
    def has_thirteen_unique_nodes(self) -> bool:
        return self.unique_node_count == 13
