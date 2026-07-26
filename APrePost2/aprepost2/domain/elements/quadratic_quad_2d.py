from .base import ElementCategory, FlatElement, PayloadFormat


class QuadraticQuad2D(FlatElement):
    """Payload A：二阶四边形二维实体，先 4 个角点，后 4 个边节点。"""

    __slots__ = ()
    CATEGORY = ElementCategory.SOLID_2D
    PAYLOAD_FORMAT = PayloadFormat.A
    COMPATIBLE_TYPES = frozenset({102, 103, 104})
    FIXED_NODE_COUNT = 8
    CORNER_INDICES = (0, 1, 2, 3)
    EDGE_NODE_INDICES = (4, 5, 6, 7)
    FACE_COUNT = 1
    POLYNOMIAL_ORDER = 2
    is_2d_solid = True
