from .element import BaseElement, create_element, replace_element_type
from .mesh import Mesh, Node

# 向后兼容别名 / backward-compatible alias
Element = BaseElement

__all__ = [
    "Node", "Element", "BaseElement", "Mesh",
    "create_element", "replace_element_type",
]
