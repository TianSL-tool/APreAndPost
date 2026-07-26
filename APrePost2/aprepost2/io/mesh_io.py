from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterable

from aprepost2.domain import (
    ELEMENT_TYPE_REGISTRY,
    BaseElement,
    Mesh,
    Node,
    create_element,
)
from aprepost2.io.text import detect_text_encoding


def _parse_element(values: tuple[int, ...], source: Path, line_number: int) -> BaseElement:
    """将解析后的整数值委托给工厂函数创建正确的单元子类。

    Delegate parsed integer values to the factory to create the correct
    element subclass.
    """
    attributes = values[:6]
    payload = values[6:]
    try:
        return create_element(*attributes, payload)
    except ValueError as exc:
        t_id = attributes[1]
        if t_id not in ELEMENT_TYPE_REGISTRY:
            raise ValueError(
                f"{source} 第 {line_number} 行：不支持的元素类型 "
                f"/ unsupported element type {t_id}"
            ) from None
        raise ValueError(
            f"{source} 第 {line_number} 行：t_id={t_id} 单元数据解析失败 / "
            f"failed to parse element data: {exc}"
        ) from exc


def read_mesh(path: str | Path, *, validate: bool = True) -> Mesh:
    source = Path(path).expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"网格文件不存在：{source}")

    nodes: list[Node] = []
    elements: list[BaseElement] = []
    section: str | None = None
    encoding = detect_text_encoding(source)

    with source.open("r", encoding=encoding, buffering=8 * 1024 * 1024) as stream:
        for line_number, raw_line in enumerate(stream, 1):
            line = raw_line.strip()
            if not line:
                continue
            marker = line.lower()
            if marker == "node":
                section = "node"
                continue
            if marker == "end node":
                section = None
                continue
            if marker == "element":
                section = "element"
                continue
            if marker == "end element":
                section = None
                continue
            try:
                parts = line.split()
                if section == "node":
                    if len(parts) != 11:
                        raise ValueError(f"节点记录应为 11 列，实际为 {len(parts)} 列")
                    nodes.append(
                        Node(
                            int(parts[0]),
                            float(parts[1]),
                            float(parts[2]),
                            float(parts[3]),
                            *(int(float(value)) for value in parts[4:11]),
                        )
                    )
                elif section == "element":
                    if len(parts) < 7:
                        raise ValueError("单元记录至少应包含 6 个属性和 1 个节点")
                    values = tuple(int(value) for value in parts)
                    elements.append(_parse_element(values, source, line_number))
                else:
                    # 与旧格式兼容：忽略两个标准区段之外的说明行。
                    continue
            except (TypeError, ValueError) as error:
                raise ValueError(f"{source} 第 {line_number} 行格式错误：{error}") from error

    if not nodes:
        raise ValueError(f"网格文件未包含节点：{source}")
    if not elements:
        raise ValueError(f"网格文件未包含单元：{source}")
    mesh = Mesh(nodes, elements)
    if validate:
        mesh.validate_connectivity()
    return mesh


def _write_content(stream, nodes: Iterable[Node], elements: Iterable[BaseElement]) -> None:
    stream.write("node\n")
    for node in nodes:
        stream.write(
            f"{node.node_id:8d} {node.x:16.10f} {node.y:16.10f} "
            f"{node.z:16.10f} {node.ux:8d} {node.uy:8d} {node.uz:8d} "
            f"{node.press:8d} {node.rx:8d} {node.ry:8d} {node.rz:8d}\n"
        )
    stream.write("end node\nelement\n")
    for element in elements:
        attributes = (
            element.e_id,
            element.t_id,
            element.c_id,
            element.m_id,
            element.d_id,
            element.f_id,
            *element.topology_payload(),
        )
        stream.write(" ".join(f"{value:8d}" for value in attributes) + "\n")
    stream.write("end element\n")


def write_mesh(
    path: str | Path,
    mesh: Mesh,
    *,
    nodes: Iterable[Node] | None = None,
    elements: Iterable[BaseElement] | None = None,
    overwrite: bool = False,
) -> Path:
    target = Path(path).expanduser().resolve()
    if target.exists() and not overwrite:
        raise FileExistsError(f"输出文件已存在：{target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    selected_nodes = mesh.nodes if nodes is None else nodes
    selected_elements = mesh.elements if elements is None else elements

    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="\n",
            buffering=8 * 1024 * 1024,
            dir=target.parent,
            prefix=f".{target.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = temporary.name
            _write_content(temporary, selected_nodes, selected_elements)
        os.replace(temporary_path, target)
        temporary_path = None
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.remove(temporary_path)
    return target
