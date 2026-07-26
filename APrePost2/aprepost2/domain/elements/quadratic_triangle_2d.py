from .base import ElementCategory, FlatElement, PayloadFormat


class QuadraticTriangle2D(FlatElement):
    """Payload A：二阶三角形二维实体，先 3 个角点，后 3 个边节点。"""

    __slots__ = ()
    CATEGORY = ElementCategory.SOLID_2D
    PAYLOAD_FORMAT = PayloadFormat.A
    COMPATIBLE_TYPES = frozenset({11, 121, 122})
    FIXED_NODE_COUNT = 6
    CORNER_INDICES = (0, 1, 2)
    EDGE_NODE_INDICES = (3, 4, 5)
    FACE_COUNT = 1
    POLYNOMIAL_ORDER = 2
    is_2d_solid = True
