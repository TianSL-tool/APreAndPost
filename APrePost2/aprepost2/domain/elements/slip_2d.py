from .base import ElementCategory, FlatElement, PayloadFormat


class Slip2D(FlatElement):
    """Payload A：四节点二维接触面。"""

    __slots__ = ()
    CATEGORY = ElementCategory.CONTACT_2D
    PAYLOAD_FORMAT = PayloadFormat.A
    COMPATIBLE_TYPES = frozenset({4, 700, 777})
    FIXED_NODE_COUNT = 4
    CORNER_INDICES = tuple(range(4))
    is_interface = True
