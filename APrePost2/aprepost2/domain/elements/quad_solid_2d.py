from .base import ElementCategory, FlatElement, PayloadFormat


class QuadSolid2D(FlatElement):
    """Payload A：四节点二维四边形实体。"""

    __slots__ = ()
    CATEGORY = ElementCategory.SOLID_2D
    PAYLOAD_FORMAT = PayloadFormat.A
    COMPATIBLE_TYPES = frozenset({1, 2, 222})
    FIXED_NODE_COUNT = 4
    is_2d_solid = True
