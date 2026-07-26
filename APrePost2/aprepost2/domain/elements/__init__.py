"""APrePost2 单元模型包。每个具体单元类位于独立模块。"""

from .base import BaseElement, ElementCategory, FlatElement, PayloadFormat
from .edge_structured_2d import EdgeStructured2D
from .hex_contact import HexContact
from .hexahedron import Hexahedron
from .higher_order import HigherOrder, HigherOrderEdge
from .higher_order_hexahedron import HigherOrderHexahedron
from .higher_order_slip_3d import HigherOrderSlip3D
from .higher_order_wedge import HigherOrderWedge
from .higher_order_wedge_alt import HigherOrderWedgeAlt
from .polygon_contact import PolygonContact
from .polygon_solid_2d import PolygonSolid2D
from .polyhedron import Polyhedron
from .quad_solid_2d import QuadSolid2D
from .quadratic_quad_2d import QuadraticQuad2D
from .quadratic_triangle_2d import QuadraticTriangle2D
from .quad_structured_contact import QuadStructuredContact
from .registry import (
    ELEMENT_TYPE_REGISTRY,
    compatible_t_ids_for_response,
    create_element,
    preferred_t_id_for_response,
    replace_element_type,
)
from .response import (
    ELEMENT_RESPONSE_TYPE_BY_T_ID,
    ElementResponseType,
    element_response_label,
    element_response_type,
)
from .slip_2d import Slip2D
from .slip_3d import Slip3D
from .structured_contact import StructuredContact
from .tri_structured_contact import TriStructuredContact

Element = BaseElement

__all__ = [
    "ElementCategory",
    "PayloadFormat",
    "ElementResponseType",
    "BaseElement",
    "FlatElement",
    "Element",
    "QuadSolid2D",
    "QuadraticQuad2D",
    "QuadraticTriangle2D",
    "PolygonSolid2D",
    "EdgeStructured2D",
    "Hexahedron",
    "HigherOrderHexahedron",
    "HigherOrderWedge",
    "HigherOrderWedgeAlt",
    "Polyhedron",
    "HigherOrder",
    "HigherOrderEdge",
    "Slip2D",
    "HexContact",
    "Slip3D",
    "HigherOrderSlip3D",
    "PolygonContact",
    "StructuredContact",
    "QuadStructuredContact",
    "TriStructuredContact",
    "ELEMENT_TYPE_REGISTRY",
    "ELEMENT_RESPONSE_TYPE_BY_T_ID",
    "create_element",
    "replace_element_type",
    "element_response_type",
    "element_response_label",
    "compatible_t_ids_for_response",
    "preferred_t_id_for_response",
]
