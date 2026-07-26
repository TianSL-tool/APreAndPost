from .base import ElementCategory, FlatElement, PayloadFormat


class HigherOrderWedge(FlatElement):
    """Payload A：15 节点二阶三棱柱 A，竖边中点先于顶边中点。"""

    __slots__ = ()
    CATEGORY = ElementCategory.SOLID_3D
    PAYLOAD_FORMAT = PayloadFormat.A
    COMPATIBLE_TYPES = frozenset({18, 170, 171})
    FIXED_NODE_COUNT = 15
    CORNER_INDICES = tuple(range(6))
    EDGE_NODE_INDICES = tuple(range(6, 15))
    FACE_COUNT = 5
    POLYNOMIAL_ORDER = 2
    is_3d_solid = True
