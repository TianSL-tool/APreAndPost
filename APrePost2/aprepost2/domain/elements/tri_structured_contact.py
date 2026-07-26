from .structured_contact import StructuredContact


class TriStructuredContact(StructuredContact):
    """Payload G：三角形跨阶接触面（t_id=224）。"""

    __slots__ = ()
    COMPATIBLE_TYPES = frozenset({224})
    PREAMBLE_SIZE = 3
    CORNER_COUNT = 3
