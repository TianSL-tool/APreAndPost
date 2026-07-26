from .base import ElementCategory, FlatElement, PayloadFormat


class HigherOrderSlip3D(FlatElement):
    """Payload A：16 节点二阶空间四边形接触面。"""

    __slots__ = ()
    CATEGORY = ElementCategory.CONTACT_3D
    PAYLOAD_FORMAT = PayloadFormat.A
    COMPATIBLE_TYPES = frozenset({21})
    FIXED_NODE_COUNT = 16
    CORNER_INDICES = (0, 1, 2, 3, 8, 9, 10, 11)
    EDGE_NODE_INDICES = (4, 5, 6, 7, 12, 13, 14, 15)
    POLYNOMIAL_ORDER = 2
    is_interface = True
