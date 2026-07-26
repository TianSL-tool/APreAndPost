"""单元响应类型标识与同拓扑响应类型查询。"""

from __future__ import annotations

from enum import Enum


class ElementResponseType(str, Enum):
    """单元求解响应类型。

    single_phase：单相；
    saturated_porous_direct：饱和多孔介质直接求解；
    saturated_porous_staggered：饱和多孔介质交叉迭代。
    """

    SINGLE_PHASE = "single_phase"
    SATURATED_POROUS_DIRECT = "saturated_porous_direct"
    SATURATED_POROUS_STAGGERED = "saturated_porous_staggered"

    @property
    def label(self) -> str:
        return _RESPONSE_LABELS[self]


_RESPONSE_LABELS = {
    ElementResponseType.SINGLE_PHASE: "单相",
    ElementResponseType.SATURATED_POROUS_DIRECT: "饱和多孔介质直接求解",
    ElementResponseType.SATURATED_POROUS_STAGGERED: "饱和多孔介质交叉迭代",
}

ELEMENT_RESPONSE_TYPE_BY_T_ID: dict[int, ElementResponseType] = {
    1: ElementResponseType.SINGLE_PHASE,
    2: ElementResponseType.SATURATED_POROUS_DIRECT,
    222: ElementResponseType.SATURATED_POROUS_STAGGERED,
    4: ElementResponseType.SINGLE_PHASE,
    700: ElementResponseType.SATURATED_POROUS_DIRECT,
    777: ElementResponseType.SATURATED_POROUS_STAGGERED,
    5: ElementResponseType.SATURATED_POROUS_DIRECT,
    6: ElementResponseType.SINGLE_PHASE,
    61: ElementResponseType.SINGLE_PHASE,
    500: ElementResponseType.SATURATED_POROUS_STAGGERED,
    9: ElementResponseType.SINGLE_PHASE,
    902: ElementResponseType.SATURATED_POROUS_DIRECT,
    903: ElementResponseType.SATURATED_POROUS_STAGGERED,
    11: ElementResponseType.SINGLE_PHASE,
    102: ElementResponseType.SATURATED_POROUS_DIRECT,
    103: ElementResponseType.SATURATED_POROUS_DIRECT,
    104: ElementResponseType.SATURATED_POROUS_STAGGERED,
    16: ElementResponseType.SINGLE_PHASE,
    510: ElementResponseType.SATURATED_POROUS_DIRECT,
    511: ElementResponseType.SATURATED_POROUS_STAGGERED,
    18: ElementResponseType.SINGLE_PHASE,
    170: ElementResponseType.SATURATED_POROUS_DIRECT,
    171: ElementResponseType.SATURATED_POROUS_STAGGERED,
    20: ElementResponseType.SINGLE_PHASE,
    190: ElementResponseType.SATURATED_POROUS_DIRECT,
    191: ElementResponseType.SATURATED_POROUS_STAGGERED,
    21: ElementResponseType.SINGLE_PHASE,
    22: ElementResponseType.SINGLE_PHASE,
    44: ElementResponseType.SINGLE_PHASE,
    47: ElementResponseType.SATURATED_POROUS_DIRECT,
    470: ElementResponseType.SATURATED_POROUS_STAGGERED,
    53: ElementResponseType.SINGLE_PHASE,
    57: ElementResponseType.SINGLE_PHASE,
    59: ElementResponseType.SINGLE_PHASE,
    80: ElementResponseType.SATURATED_POROUS_DIRECT,
    800: ElementResponseType.SATURATED_POROUS_STAGGERED,
    60: ElementResponseType.SINGLE_PHASE,
    601: ElementResponseType.SATURATED_POROUS_DIRECT,
    602: ElementResponseType.SATURATED_POROUS_STAGGERED,
    121: ElementResponseType.SATURATED_POROUS_DIRECT,
    122: ElementResponseType.SATURATED_POROUS_STAGGERED,
    223: ElementResponseType.SINGLE_PHASE,
    224: ElementResponseType.SINGLE_PHASE,
    443: ElementResponseType.SINGLE_PHASE,
    444: ElementResponseType.SATURATED_POROUS_DIRECT,
    644: ElementResponseType.SATURATED_POROUS_STAGGERED,
    508: ElementResponseType.SINGLE_PHASE,
    805: ElementResponseType.SATURATED_POROUS_DIRECT,
    807: ElementResponseType.SATURATED_POROUS_STAGGERED,
}


def element_response_type(t_id: int) -> ElementResponseType:
    """返回单元类型号对应的响应类型。"""

    try:
        return ELEMENT_RESPONSE_TYPE_BY_T_ID[int(t_id)]
    except KeyError as exc:
        raise ValueError(f"单元类型 {t_id} 尚未配置响应类型") from exc


def element_response_label(t_id: int) -> str:
    """返回单元类型号对应的中文响应类型名称。"""

    return element_response_type(t_id).label

