from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable

import numpy as np

if TYPE_CHECKING:
    from aprepost2.domain.element import BaseElement


@dataclass(slots=True)
class Node:
    node_id: int
    x: float
    y: float
    z: float
    ux: int = 0
    uy: int = 0
    uz: int = 0
    press: int = 0
    rx: int = 0
    ry: int = 0
    rz: int = 0

    @property
    def coordinates(self) -> tuple[float, float, float]:
        return self.x, self.y, self.z


@dataclass(slots=True)
class Mesh:
    nodes: list[Node]
    elements: list[BaseElement]
    node_map: dict[int, Node] = field(init=False, repr=False)
    element_map: dict[int, BaseElement] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.node_map = {node.node_id: node for node in self.nodes}
        self.element_map = {element.e_id: element for element in self.elements}
        if len(self.node_map) != len(self.nodes):
            raise ValueError("网格中存在重复节点编号")
        if len(self.element_map) != len(self.elements):
            raise ValueError("网格中存在重复单元编号")

    def validate_connectivity(self) -> None:
        missing: list[tuple[int, int]] = []
        for element in self.elements:
            for node_id in element.node_ids:
                if node_id not in self.node_map:
                    missing.append((element.e_id, node_id))
                    if len(missing) >= 10:
                        break
            if len(missing) >= 10:
                break
        if missing:
            details = "，".join(f"单元{eid}->节点{nid}" for eid, nid in missing)
            raise ValueError(f"单元引用了不存在的节点：{details}")

    def invalidate_geometry_cache(self) -> None:
        for element in self.elements:
            element.invalidate_geometry_cache()

    def coordinates_array(self, nodes: Iterable[Node] | None = None) -> np.ndarray:
        source = self.nodes if nodes is None else nodes
        return np.asarray([node.coordinates for node in source], dtype=np.float64)
