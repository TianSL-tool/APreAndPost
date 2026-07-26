"""单元类型注册、解析分派与同结构类型转换。"""

from .base import BaseElement
from .edge_structured_2d import EdgeStructured2D
from .hex_contact import HexContact
from .hexahedron import Hexahedron
from .higher_order import HigherOrder
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
from .response import (
    ELEMENT_RESPONSE_TYPE_BY_T_ID,
    ElementResponseType,
)
from .slip_2d import Slip2D
from .slip_3d import Slip3D
from .tri_structured_contact import TriStructuredContact


ELEMENT_TYPE_REGISTRY: dict[int, type[BaseElement]] = {
    **{t_id: QuadSolid2D for t_id in QuadSolid2D.COMPATIBLE_TYPES},
    **{t_id: QuadraticQuad2D for t_id in QuadraticQuad2D.COMPATIBLE_TYPES},
    **{
        t_id: QuadraticTriangle2D
        for t_id in QuadraticTriangle2D.COMPATIBLE_TYPES
    },
    **{t_id: PolygonSolid2D for t_id in PolygonSolid2D.COMPATIBLE_TYPES},
    **{t_id: EdgeStructured2D for t_id in EdgeStructured2D.COMPATIBLE_TYPES},
    **{t_id: Hexahedron for t_id in Hexahedron.COMPATIBLE_TYPES},
    **{
        t_id: HigherOrderHexahedron
        for t_id in HigherOrderHexahedron.COMPATIBLE_TYPES
    },
    **{t_id: HigherOrderWedge for t_id in HigherOrderWedge.COMPATIBLE_TYPES},
    **{
        t_id: HigherOrderWedgeAlt
        for t_id in HigherOrderWedgeAlt.COMPATIBLE_TYPES
    },
    **{t_id: Polyhedron for t_id in Polyhedron.COMPATIBLE_TYPES},
    **{t_id: HigherOrder for t_id in HigherOrder.COMPATIBLE_TYPES},
    **{t_id: Slip2D for t_id in Slip2D.COMPATIBLE_TYPES},
    **{t_id: HexContact for t_id in HexContact.COMPATIBLE_TYPES},
    **{t_id: Slip3D for t_id in Slip3D.COMPATIBLE_TYPES},
    **{
        t_id: HigherOrderSlip3D
        for t_id in HigherOrderSlip3D.COMPATIBLE_TYPES
    },
    **{t_id: PolygonContact for t_id in PolygonContact.COMPATIBLE_TYPES},
    **{
        t_id: QuadStructuredContact
        for t_id in QuadStructuredContact.COMPATIBLE_TYPES
    },
    **{
        t_id: TriStructuredContact
        for t_id in TriStructuredContact.COMPATIBLE_TYPES
    },
}


def create_element(
    e_id: int,
    t_id: int,
    c_id: int,
    m_id: int,
    d_id: int,
    f_id: int,
    payload: tuple[int, ...],
) -> BaseElement:
    element_class = ELEMENT_TYPE_REGISTRY.get(int(t_id))
    if element_class is None:
        raise ValueError(f"不支持的单元类型：{t_id}")
    return element_class.from_parsed(
        e_id, t_id, c_id, m_id, d_id, f_id, tuple(payload)
    )


def replace_element_type(element: BaseElement, new_t_id: int) -> BaseElement:
    new_t_id = int(new_t_id)
    target_class = ELEMENT_TYPE_REGISTRY.get(new_t_id)
    if target_class is None:
        raise ValueError(
            f"尚未注册安全的单元转换规则：{element.t_id} -> {new_t_id}，"
            f"目标类型不受支持"
        )
    if new_t_id not in element.COMPATIBLE_TYPES or target_class is not type(element):
        raise ValueError(
            f"不允许仅修改类型号完成跨拓扑转换：{element.t_id} -> {new_t_id}"
        )
    return target_class.from_parsed(
        element.e_id,
        new_t_id,
        element.c_id,
        element.m_id,
        element.d_id,
        element.f_id,
        element.topology_payload(),
    )


def compatible_t_ids_for_response(
    source_t_id: int,
    target_response: ElementResponseType,
) -> tuple[int, ...]:
    """返回同一具体拓扑类中匹配目标响应类型的可转换 t_id。"""

    source_t_id = int(source_t_id)
    source_class = ELEMENT_TYPE_REGISTRY.get(source_t_id)
    if source_class is None:
        raise ValueError(f"不支持的单元类型：{source_t_id}")
    target_response = ElementResponseType(target_response)
    return tuple(
        t_id
        for t_id in sorted(source_class.COMPATIBLE_TYPES)
        if t_id in ELEMENT_TYPE_REGISTRY
        and ELEMENT_TYPE_REGISTRY[t_id] is source_class
        and ELEMENT_RESPONSE_TYPE_BY_T_ID.get(t_id) == target_response
    )


def preferred_t_id_for_response(
    source_t_id: int,
    target_response: ElementResponseType,
) -> int:
    """返回同一拓扑类中目标响应类型的首选 t_id。

    若同一响应类型存在多个候选，例如 Hexahedron 的单相 `6` 与 `61`，
    调用方应使用 `compatible_t_ids_for_response()` 自行选择；本函数默认返回
    排序后的第一个候选，便于无歧义类型的转换入口使用。
    """

    candidates = compatible_t_ids_for_response(source_t_id, target_response)
    if not candidates:
        raise ValueError(
            f"单元类型 {source_t_id} 的同拓扑类型中没有 "
            f"{ElementResponseType(target_response).label} 响应"
        )
    return candidates[0]
