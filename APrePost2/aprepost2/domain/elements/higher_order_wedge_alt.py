from .base import ElementCategory, FlatElement, PayloadFormat


class HigherOrderWedgeAlt(FlatElement):
    """Payload A：15 节点二阶三棱柱 B，顶边中点先于竖边中点。"""

    __slots__ = ()
    CATEGORY = ElementCategory.SOLID_3D
    PAYLOAD_FORMAT = PayloadFormat.A
    COMPATIBLE_TYPES = frozenset({20, 190, 191})
    FIXED_NODE_COUNT = 15
    CORNER_INDICES = tuple(range(6))
    EDGE_NODE_INDICES = tuple(range(6, 15))
    FACE_COUNT = 5
    POLYNOMIAL_ORDER = 2
    is_3d_solid = True
