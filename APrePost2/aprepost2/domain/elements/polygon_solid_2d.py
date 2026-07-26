from .base import ElementCategory, FlatElement, PayloadFormat


class PolygonSolid2D(FlatElement):
    """Payload B：可变节点二维多边形实体。"""

    __slots__ = ()
    CATEGORY = ElementCategory.SOLID_2D
    PAYLOAD_FORMAT = PayloadFormat.B
    COMPATIBLE_TYPES = frozenset({44, 47, 470})
    MIN_NODE_COUNT = 3
    is_2d_solid = True
