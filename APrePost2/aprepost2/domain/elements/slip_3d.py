from .base import ElementCategory, FlatElement, PayloadFormat


class Slip3D(FlatElement):
    """Payload B：结构尚未明确的 t_id=22 三维接触面。"""

    __slots__ = ()
    CATEGORY = ElementCategory.CONTACT_3D
    PAYLOAD_FORMAT = PayloadFormat.B
    COMPATIBLE_TYPES = frozenset({22})
    MIN_NODE_COUNT = 1
    CORNER_INDICES = ()
    POLYNOMIAL_ORDER = None
    is_interface = True
