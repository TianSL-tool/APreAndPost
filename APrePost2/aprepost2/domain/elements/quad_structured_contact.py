from .structured_contact import StructuredContact


class QuadStructuredContact(StructuredContact):
    """Payload G：四边形跨阶接触面（t_id=223）。"""

    __slots__ = ()
    COMPATIBLE_TYPES = frozenset({223})
    PREAMBLE_SIZE = 4
    CORNER_COUNT = 4
