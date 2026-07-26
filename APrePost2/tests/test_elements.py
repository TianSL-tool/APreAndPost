from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

from aprepost2.domain.element import (
    ELEMENT_TYPE_REGISTRY,
    ELEMENT_RESPONSE_TYPE_BY_T_ID,
    EdgeStructured2D,
    ElementResponseType,
    HexContact,
    Hexahedron,
    HigherOrder,
    HigherOrderEdge,
    HigherOrderHexahedron,
    HigherOrderSlip3D,
    HigherOrderWedge,
    HigherOrderWedgeAlt,
    PayloadFormat,
    PolygonContact,
    PolygonSolid2D,
    Polyhedron,
    QuadSolid2D,
    QuadraticQuad2D,
    QuadraticTriangle2D,
    QuadStructuredContact,
    Slip2D,
    Slip3D,
    TriStructuredContact,
    compatible_t_ids_for_response,
    create_element,
    element_response_label,
    element_response_type,
    preferred_t_id_for_response,
    replace_element_type,
)
from aprepost2.domain.mesh import Node
from aprepost2.io.mesh_io import read_mesh, write_mesh
from aprepost2.services.mesh_operations import (
    _hex20_faces,
    _offset_topology_payload,
    _wedge15_faces,
    convert_element_topology,
    convert_to_higher_order,
)


def make(t_id: int, payload: tuple[int, ...]):
    return create_element(1, t_id, 10, 20, 30, 40, payload)


AUTHORITATIVE_508_PAYLOAD = tuple(
    int(value)
    for value in (
        "6 4 4 4 4 4 4 "
        + "2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 2 "
        + "1 2 6 5 9 14 17 13 "
        + "4 8 7 3 16 19 15 11 "
        + "1 4 3 2 12 11 10 9 "
        + "1 5 8 4 13 20 16 12 "
        + "5 6 7 8 17 18 19 20 "
        + "2 3 7 6 10 15 18 14"
    ).split()
)


class ElementStructureTests(unittest.TestCase):
    def test_node_id_offset_preserves_all_payload_metadata(self):
        cases = (
            make(6, tuple(range(1, 9))),
            make(
                57,
                (4, 3, 3, 3, 3, 1, 2, 3, 1, 4, 2, 2, 4, 3, 3, 4, 1),
            ),
            make(444, (4, 1, 2, 1, 2, 1, 2, 3, 4, 6, 8)),
            make(508, (4, 3, 3, 3, 3, *([1] * 12), *range(101, 113))),
            make(60, (1, 2, 3, 4, 5, 6)),
            make(223, (1, 0, 1, 0, *range(1, 13))),
        )
        for element in cases:
            with self.subTest(payload_format=element.PAYLOAD_FORMAT):
                shifted = create_element(
                    element.e_id + 200,
                    element.t_id,
                    element.c_id,
                    element.m_id,
                    element.d_id,
                    element.f_id,
                    _offset_topology_payload(element, 1000),
                )
                self.assertEqual(shifted.e_id, 201)
                self.assertEqual(
                    shifted.node_ids,
                    tuple(node_id + 1000 for node_id in element.node_ids),
                )
                self.assertEqual(shifted.PAYLOAD_FORMAT, element.PAYLOAD_FORMAT)
                self.assertEqual(shifted.face_count, element.face_count)

    def test_type_registry_exact_mapping(self):
        expected = {
            1: QuadSolid2D,
            2: QuadSolid2D,
            222: QuadSolid2D,
            102: QuadraticQuad2D,
            103: QuadraticQuad2D,
            104: QuadraticQuad2D,
            11: QuadraticTriangle2D,
            121: QuadraticTriangle2D,
            122: QuadraticTriangle2D,
            44: PolygonSolid2D,
            47: PolygonSolid2D,
            470: PolygonSolid2D,
            443: EdgeStructured2D,
            444: EdgeStructured2D,
            644: EdgeStructured2D,
            5: Hexahedron,
            6: Hexahedron,
            23: Hexahedron,
            61: Hexahedron,
            500: Hexahedron,
            16: HigherOrderHexahedron,
            510: HigherOrderHexahedron,
            511: HigherOrderHexahedron,
            18: HigherOrderWedge,
            170: HigherOrderWedge,
            171: HigherOrderWedge,
            20: HigherOrderWedgeAlt,
            190: HigherOrderWedgeAlt,
            191: HigherOrderWedgeAlt,
            53: Polyhedron,
            57: Polyhedron,
            59: Polyhedron,
            80: Polyhedron,
            800: Polyhedron,
            508: HigherOrder,
            805: HigherOrder,
            807: HigherOrder,
            4: Slip2D,
            700: Slip2D,
            777: Slip2D,
            9: HexContact,
            902: HexContact,
            903: HexContact,
            22: Slip3D,
            21: HigherOrderSlip3D,
            60: PolygonContact,
            601: PolygonContact,
            602: PolygonContact,
            223: QuadStructuredContact,
            224: TriStructuredContact,
        }
        self.assertEqual(ELEMENT_TYPE_REGISTRY, expected)

    def test_concrete_element_classes_live_in_separate_modules(self):
        concrete_classes = tuple(set(ELEMENT_TYPE_REGISTRY.values()))
        modules = [element_class.__module__ for element_class in concrete_classes]
        self.assertEqual(len(modules), len(set(modules)))
        self.assertTrue(
            all(module.startswith("aprepost2.domain.elements.") for module in modules)
        )

    def test_element_response_type_mapping(self):
        self.assertEqual(
            element_response_type(1),
            ElementResponseType.SINGLE_PHASE,
        )
        self.assertEqual(
            element_response_type(2),
            ElementResponseType.SATURATED_POROUS_DIRECT,
        )
        self.assertEqual(
            element_response_type(222),
            ElementResponseType.SATURATED_POROUS_STAGGERED,
        )
        self.assertEqual(element_response_type(11), ElementResponseType.SINGLE_PHASE)
        self.assertEqual(element_response_type(121), ElementResponseType.SATURATED_POROUS_DIRECT)
        self.assertEqual(element_response_type(122), ElementResponseType.SATURATED_POROUS_STAGGERED)
        self.assertEqual(element_response_label(805), "饱和多孔介质直接求解")
        self.assertEqual(
            compatible_t_ids_for_response(
                121, ElementResponseType.SINGLE_PHASE
            ),
            (11,),
        )
        self.assertEqual(
            compatible_t_ids_for_response(
                5, ElementResponseType.SINGLE_PHASE
            ),
            (6, 61),
        )
        self.assertEqual(
            preferred_t_id_for_response(
                805, ElementResponseType.SATURATED_POROUS_STAGGERED
            ),
            807,
        )
        self.assertNotIn(23, ELEMENT_RESPONSE_TYPE_BY_T_ID)

    def test_payload_a_fixed_node_counts(self):
        cases = (
            (1, QuadSolid2D, 4),
            (102, QuadraticQuad2D, 8),
            (11, QuadraticTriangle2D, 6),
            (121, QuadraticTriangle2D, 6),
            (6, Hexahedron, 8),
            (16, HigherOrderHexahedron, 20),
            (18, HigherOrderWedge, 15),
            (20, HigherOrderWedgeAlt, 15),
            (4, Slip2D, 4),
            (9, HexContact, 8),
            (21, HigherOrderSlip3D, 16),
        )
        for t_id, expected_class, node_count in cases:
            with self.subTest(t_id=t_id):
                payload = tuple(range(1, node_count + 1))
                element = make(t_id, payload)
                self.assertIsInstance(element, expected_class)
                self.assertEqual(element.topology_payload(), payload)
                with self.assertRaises(ValueError):
                    make(t_id, payload[:-1])

    def test_fixed_elements_remember_semantic_node_groups(self):
        quad8 = make(102, tuple(range(1, 9)))
        self.assertEqual(quad8.corner_node_ids, (1, 2, 3, 4))
        self.assertEqual(quad8.edge_node_ids, (5, 6, 7, 8))
        self.assertEqual(quad8.polynomial_order, 2)

        tri6 = make(11, tuple(range(11, 17)))
        self.assertEqual(tri6.corner_node_ids, (11, 12, 13))
        self.assertEqual(tri6.edge_node_ids, (14, 15, 16))
        self.assertEqual(tri6.polynomial_order, 2)

        hexa20 = make(16, tuple(range(1, 21)))
        self.assertEqual(hexa20.corner_node_ids, tuple(range(1, 9)))
        self.assertEqual(hexa20.edge_node_ids, tuple(range(9, 21)))
        self.assertEqual(hexa20.face_count, 6)
        self.assertEqual(hexa20.polynomial_order, 2)

        wedge_a = make(18, tuple(range(1, 16)))
        wedge_b = make(20, tuple(range(21, 36)))
        self.assertEqual(wedge_a.corner_node_ids, tuple(range(1, 7)))
        self.assertEqual(wedge_a.edge_node_ids, tuple(range(7, 16)))
        self.assertEqual(wedge_a.face_count, 5)
        self.assertEqual(wedge_b.corner_node_ids, tuple(range(21, 27)))
        self.assertEqual(wedge_b.edge_node_ids, tuple(range(27, 36)))

        slip = make(21, tuple(range(1, 17)))
        self.assertEqual(slip.corner_node_ids, (1, 2, 3, 4, 9, 10, 11, 12))
        self.assertEqual(slip.edge_node_ids, (5, 6, 7, 8, 13, 14, 15, 16))
        self.assertEqual(slip.topology_payload(), tuple(range(1, 17)))

    def test_payload_b_variable_node_lists(self):
        polygon = make(44, (1, 2, 3, 4, 5))
        slip = make(22, (10, 11, 12))
        self.assertEqual(polygon.PAYLOAD_FORMAT, PayloadFormat.B)
        self.assertEqual(polygon.node_ids, (1, 2, 3, 4, 5))
        self.assertEqual(slip.node_ids, (10, 11, 12))
        with self.assertRaises(ValueError):
            make(44, (1, 2))
        with self.assertRaises(ValueError):
            make(22, ())

    def test_payload_c_polyhedron(self):
        payload = (
            4,
            3,
            3,
            3,
            3,
            1,
            2,
            3,
            1,
            4,
            2,
            2,
            4,
            3,
            3,
            4,
            1,
        )
        element = make(57, payload)
        self.assertEqual(element.faces(), ((1, 2, 3), (1, 4, 2), (2, 4, 3), (3, 4, 1)))
        self.assertEqual(element.topology_payload(), payload)
        structured = Polyhedron.from_faces(
            2, 59, 1, 2, 3, 4, element.faces()
        )
        self.assertEqual(structured.topology_payload(), payload)
        with self.assertRaises(ValueError):
            make(57, payload[:-1])

    def test_polyhedron_checks_right_hand_outward_face_order(self):
        node_map = {
            1: Node(1, 0, 0, 0),
            2: Node(2, 1, 0, 0),
            3: Node(3, 0, 1, 0),
            4: Node(4, 0, 0, 1),
        }
        outward = Polyhedron.from_faces(
            1,
            57,
            1,
            2,
            3,
            4,
            ((3, 2, 1), (1, 2, 4), (2, 3, 4), (3, 1, 4)),
        )
        self.assertTrue(outward.faces_are_oriented_outward(node_map))

        inward_face = Polyhedron.from_faces(
            1,
            57,
            1,
            2,
            3,
            4,
            ((1, 2, 3), (1, 2, 4), (2, 3, 4), (3, 1, 4)),
        )
        violations = inward_face.face_orientation_violations(node_map)
        self.assertEqual(violations[0][0], 1)
        self.assertIn("内侧", violations[0][1])

    def test_payload_d_edge_structured(self):
        payload = (4, 2, 3, 2, 3, *range(1, 11))
        element = make(443, payload)
        self.assertEqual(element.edge_count, 4)
        self.assertEqual(element.edge_sizes, (2, 3, 2, 3))
        self.assertEqual(element.edge_node_groups[1], (3, 4, 5))
        self.assertEqual(element.corner_node_ids, (1, 3, 6, 8))
        self.assertEqual(element.node_ids, tuple(range(1, 11)))
        self.assertEqual(element.topology_payload(), payload)
        with self.assertRaises(ValueError):
            make(443, payload[:-1])

        cross_order_payload = (4, 1, 2, 1, 2, 1, 2, 3, 4, 6, 8)
        cross_order = make(444, cross_order_payload)
        self.assertEqual(cross_order.edge_orders, (1, 2, 1, 2))
        self.assertEqual(cross_order.edge_sizes, (2, 3, 2, 3))
        self.assertEqual(cross_order.corner_node_ids, (1, 2, 3, 4))
        self.assertEqual(cross_order.edge_node_ids, (6, 8))
        self.assertEqual(
            cross_order.edge_node_groups,
            ((1, 2), (2, 6, 3), (3, 4), (4, 8, 1)),
        )
        self.assertEqual(cross_order.topology_payload(), cross_order_payload)
        self.assertIsInstance(make(644, cross_order_payload), EdgeStructured2D)
        with self.assertRaises(ValueError):
            make(444, cross_order_payload[:-1])
        structured = EdgeStructured2D.from_edges(
            2, 443, 1, 2, 3, 4, ((1, 2), (2, 3, 4), (4, 5), (5, 6, 1))
        )
        self.assertEqual(
            structured.edges(), ((1, 2), (2, 3, 4), (4, 5), (5, 6, 1))
        )

    def test_payload_e_higher_order_nested_structure(self):
        # 四个三边形面，每条边一阶，因此每面 3 个节点，共 12 个面节点。
        payload = (4, 3, 3, 3, 3, *([1] * 12), *range(101, 113))
        element = make(508, payload)
        self.assertEqual(element.nodes_per_face, (3, 3, 3, 3))
        self.assertEqual(element.face_count, 4)
        self.assertEqual(element.polynomial_order, 1)
        self.assertEqual(
            element.face_edges[0],
            ((101, 102), (102, 103), (103, 101)),
        )
        self.assertEqual(
            element.faces(),
            (
                (101, 102, 103),
                (104, 105, 106),
                (107, 108, 109),
                (110, 111, 112),
            ),
        )
        self.assertEqual(element.topology_payload(), payload)
        with self.assertRaises(ValueError):
            make(508, payload[:-1])
        structured = HigherOrder.from_structure(
            2,
            508,
            1,
            2,
            3,
            4,
            ((1, 1, 1),) * 4,
            (
                (1, 2, 3),
                (1, 4, 2),
                (2, 4, 3),
                (3, 4, 1),
            ),
        )
        self.assertEqual(structured.faces()[2], (2, 4, 3))

    def test_payload_f_polygon_contact_faces(self):
        element = make(60, (1, 2, 3, 4, 5, 6))
        self.assertEqual(
            element.faces(),
            (
                (3, 2, 1),
                (4, 5, 6),
                (1, 2, 5, 4),
                (2, 3, 6, 5),
                (3, 1, 4, 6),
            ),
        )
        with self.assertRaises(ValueError):
            make(60, (1, 2, 3, 4, 5))
        structured = PolygonContact.from_surfaces(
            2, 601, 1, 2, 3, 4, (1, 2, 3), (4, 5, 6)
        )
        self.assertEqual(structured.bottom_node_ids, (1, 2, 3))
        self.assertEqual(structured.top_node_ids, (4, 5, 6))

    def test_payload_g_quad_and_triangle_contacts(self):
        quad_payload = (1, 0, 1, 0, *range(1, 13))
        quad = make(223, quad_payload)
        self.assertEqual(quad.mid_flags, (1, 0, 1, 0))
        self.assertEqual(quad.bottom_corner_ids, (1, 2, 3, 4))
        self.assertEqual(quad.bottom_mid_ids, (5, 6))
        self.assertEqual(quad.top_corner_ids, (7, 8, 9, 10))
        self.assertEqual(quad.top_mid_ids, (11, 12))
        self.assertIsNone(quad.polynomial_order)
        self.assertEqual(quad.topology_payload(), quad_payload)

        tri_payload = (1, 1, 1, *range(21, 33))
        tri = make(224, tri_payload)
        self.assertEqual(tri.bottom_corner_ids, (21, 22, 23))
        self.assertEqual(tri.bottom_mid_ids, (24, 25, 26))
        self.assertEqual(tri.top_corner_ids, (27, 28, 29))
        self.assertEqual(tri.top_mid_ids, (30, 31, 32))
        with self.assertRaises(ValueError):
            make(223, (2, 0, 0, 0, *range(1, 9)))
        layered = QuadStructuredContact.from_layers(
            2,
            223,
            1,
            2,
            3,
            4,
            (1, 0, 1, 0),
            (1, 2, 3, 4),
            (5, 6),
            (7, 8, 9, 10),
            (11, 12),
        )
        self.assertEqual(layered.topology_payload(), quad_payload)

    def test_output_is_rebuilt_from_structured_fields(self):
        hexa20 = make(16, tuple(range(1, 21)))
        hexa20.edge_node_ids = tuple(range(109, 121))
        self.assertEqual(
            hexa20.topology_payload(),
            (*range(1, 9), *range(109, 121)),
        )

        contact = make(60, (1, 2, 3, 4, 5, 6))
        contact.top_node_ids = (14, 15, 16)
        self.assertEqual(contact.topology_payload(), (1, 2, 3, 14, 15, 16))

        structured = make(223, (1, 0, 1, 0, *range(1, 13)))
        structured.top_mid_ids = (111, 112)
        self.assertEqual(
            structured.topology_payload(),
            (1, 0, 1, 0, *range(1, 11), 111, 112),
        )

    def test_mesh_writer_uses_structured_groups(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.dat"
            target = root / "target.dat"
            nodes = "\n".join(
                f"{node_id} {node_id} 0 0 0 0 0 0 0 0 0"
                for node_id in range(1, 21)
            )
            source.write_text(
                "node\n"
                + nodes
                + "\nend node\nelement\n"
                + "1 16 1 2 3 4 "
                + " ".join(str(value) for value in range(1, 21))
                + "\nend element\n",
                encoding="utf-8",
            )
            mesh = read_mesh(source)
            mesh.elements[0].edge_node_ids = tuple(range(20, 8, -1))
            write_mesh(target, mesh)
            reread = read_mesh(target)
            self.assertEqual(
                reread.elements[0].edge_node_ids,
                tuple(range(20, 8, -1)),
            )

    def test_faces_and_degeneracy_signatures(self):
        hexa = make(6, (1, 2, 3, 3, 4, 4, 4, 4))
        self.assertTrue(hexa.is_degenerate_tetrahedron())
        self.assertEqual(len(hexa.faces()), 4)

        contact = make(9, (1, 2, 2, 3, 4, 5, 6, 7))
        self.assertTrue(contact.is_degenerate_wedge())

        higher = make(
            16,
            (
                1, 2, 3, 4,
                5, 5, 5, 5,
                6, 7, 8, 9,
                10, 10, 10, 10,
                11, 12, 13, 14,
            ),
        )
        self.assertTrue(higher.has_pyramid_degeneracy_signature())
        self.assertEqual(higher.unique_node_count, 14)
        self.assertFalse(higher.has_thirteen_unique_nodes)

    def test_type_replacement_only_within_same_structure(self):
        element = make(6, tuple(range(1, 9)))
        replacement = replace_element_type(element, 61)
        self.assertIsInstance(replacement, Hexahedron)
        self.assertEqual(replacement.t_id, 61)
        self.assertEqual(replacement.node_ids, element.node_ids)
        with self.assertRaisesRegex(ValueError, "跨拓扑"):
            replace_element_type(element, 57)

    def test_supported_topology_conversions(self):
        quad = make(1, (1, 2, 3, 4))
        polygon = convert_element_topology(quad, 44)
        self.assertIsInstance(polygon, PolygonSolid2D)
        self.assertEqual(polygon.topology_payload(), (1, 2, 3, 4))
        self.assertIsInstance(convert_element_topology(polygon, 1), QuadSolid2D)

        tri6 = make(11, (1, 2, 3, 4, 5, 6))
        edge_tri = convert_element_topology(tri6, 444)
        self.assertIsInstance(edge_tri, EdgeStructured2D)
        self.assertEqual(edge_tri.topology_payload(), (3, 2, 2, 2, 1, 2, 3, 4, 5, 6))
        self.assertIsInstance(convert_element_topology(edge_tri, 11), QuadraticTriangle2D)

        quad8 = make(102, (1, 2, 3, 4, 5, 6, 7, 8))
        edge_quad = convert_element_topology(quad8, 644)
        self.assertIsInstance(edge_quad, EdgeStructured2D)
        self.assertEqual(
            edge_quad.topology_payload(),
            (4, 2, 2, 2, 2, 1, 2, 3, 4, 5, 6, 7, 8),
        )
        self.assertIsInstance(convert_element_topology(edge_quad, 102), QuadraticQuad2D)

        hex8 = make(6, tuple(range(1, 9)))
        poly = convert_element_topology(hex8, 57)
        self.assertIsInstance(poly, Polyhedron)
        restored_hex = convert_element_topology(poly, 6)
        self.assertIsInstance(restored_hex, Hexahedron)
        self.assertEqual(set(restored_hex.faces()), set(hex8.faces()))

        hex20 = make(16, tuple(range(1, 21)))
        higher = convert_element_topology(hex20, 508)
        self.assertIsInstance(higher, HigherOrder)
        self.assertEqual(higher.face_edge_counts, (4, 4, 4, 4, 4, 4))
        auto_regular = convert_element_topology(higher, 0)
        self.assertIsInstance(auto_regular, HigherOrderHexahedron)
        self.assertEqual(auto_regular.t_id, 16)

    def test_unsupported_topology_conversion_rejects_ambiguous_reverse(self):
        polygon = make(44, (1, 2, 3, 4, 5))
        with self.assertRaisesRegex(ValueError, "不能唯一转为四节点"):
            convert_element_topology(polygon, 1)

        arbitrary = HigherOrder.from_structure(
            1,
            508,
            10,
            20,
            30,
            40,
            ((2, 2, 2), (2, 2, 2), (2, 2, 2), (2, 2, 2)),
            (
                (1, 2, 3, 4, 5, 6),
                (1, 4, 7, 8, 9, 10),
                (2, 5, 7, 11, 12, 13),
                (3, 6, 8, 14, 15, 16),
            ),
        )
        with self.assertRaisesRegex(ValueError, "无对应的常规单元"):
            convert_element_topology(arbitrary, 0)

    def test_higher_order_conversion_writes_nested_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "hex20.dat"
            target = root / "higher.dat"
            nodes = "\n".join(
                f"{node_id} {node_id} 0 0 0 0 0 0 0 0 0"
                for node_id in range(1, 21)
            )
            source.write_text(
                "node\n"
                + nodes
                + "\nend node\nelement\n"
                + "1 16 1 2 3 4 "
                + " ".join(str(value) for value in range(1, 21))
                + "\nend element\n",
                encoding="utf-8",
            )
            convert_to_higher_order(str(source), str(target))
            converted = read_mesh(target).elements[0]
            self.assertIsInstance(converted, HigherOrder)
            self.assertEqual(converted.t_id, 508)
            self.assertEqual(converted.edges_per_face, (4, 4, 4, 4, 4, 4))
            self.assertEqual(converted.orders_per_face, ((2, 2, 2, 2),) * 6)
            self.assertEqual(converted.nodes_per_face, (8, 8, 8, 8, 8, 8))
            self.assertEqual(len(converted.faces()), 6)
            self.assertEqual(
                converted.faces()[0],
                (1, 2, 6, 5, 9, 14, 17, 13),
            )
            self.assertEqual(set(converted.corner_node_ids), set(range(1, 9)))
            self.assertEqual(set(converted.edge_node_ids), set(range(9, 21)))
            self.assertFalse(
                set(converted.corner_node_ids) & set(converted.edge_node_ids)
            )
            self.assertEqual(
                converted.topology_payload(),
                AUTHORITATIVE_508_PAYLOAD,
            )

    def test_quadratic_face_mapping_uses_corner_block_then_internal_block(self):
        self.assertEqual(
            _hex20_faces(tuple(range(1, 21)))[0],
            [1, 2, 6, 5, 9, 14, 17, 13],
        )
        self.assertEqual(
            _wedge15_faces(tuple(range(1, 16)), False),
            [
                [1, 2, 5, 4, 7, 11, 13, 10],
                [2, 3, 6, 5, 8, 12, 14, 11],
                [3, 1, 4, 6, 9, 10, 15, 12],
                [1, 3, 2, 9, 8, 7],
                [4, 5, 6, 13, 14, 15],
            ],
        )
        self.assertEqual(
            _wedge15_faces(tuple(range(1, 16)), True),
            [
                [1, 2, 5, 4, 7, 14, 10, 13],
                [2, 3, 6, 5, 8, 15, 11, 14],
                [3, 1, 4, 6, 9, 13, 12, 15],
                [1, 3, 2, 9, 8, 7],
                [4, 5, 6, 10, 11, 12],
            ],
        )

    def test_payload_e_parses_authoritative_508_layout(self):
        payload = AUTHORITATIVE_508_PAYLOAD
        element = make(508, payload)
        self.assertEqual(element.n_faces, 6)
        self.assertEqual(element.face_edge_counts, (4, 4, 4, 4, 4, 4))
        self.assertEqual(element.face_edge_orders, ((2, 2, 2, 2),) * 6)
        self.assertEqual(
            element.corner_nodes,
            (
                (1, 2, 6, 5),
                (4, 8, 7, 3),
                (1, 4, 3, 2),
                (1, 5, 8, 4),
                (5, 6, 7, 8),
                (2, 3, 7, 6),
            ),
        )
        self.assertEqual(
            element.edge_internal_nodes[0],
            ((9,), (14,), (17,), (13,)),
        )
        self.assertEqual(
            element.face_nodes[0],
            (1, 2, 6, 5, 9, 14, 17, 13),
        )
        self.assertEqual(
            element.edge_maps[0],
            (
                HigherOrderEdge(1, 2, 2, (9,)),
                HigherOrderEdge(2, 6, 2, (14,)),
                HigherOrderEdge(6, 5, 2, (17,)),
                HigherOrderEdge(5, 1, 2, (13,)),
            ),
        )
        self.assertEqual(element.topology_payload(), payload)

    def test_higher_order_conversion_covers_all_source_type_mappings(self):
        source_types = (16, 510, 511, 18, 170, 171, 20, 190, 191)
        expected_targets = (508, 805, 807, 508, 805, 807, 508, 805, 807)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "all_source_types.dat"
            target = root / "all_target_types.dat"
            nodes = "\n".join(
                f"{node_id} {node_id} 0 0 0 0 0 0 0 0 0"
                for node_id in range(1, 21)
            )
            element_lines = []
            for e_id, t_id in enumerate(source_types, 1):
                node_count = 20 if t_id in (16, 510, 511) else 15
                element_lines.append(
                    f"{e_id} {t_id} 1 2 3 4 "
                    + " ".join(str(value) for value in range(1, node_count + 1))
                )
            source.write_text(
                "node\n"
                + nodes
                + "\nend node\nelement\n"
                + "\n".join(element_lines)
                + "\nend element\n",
                encoding="utf-8",
            )

            convert_to_higher_order(str(source), str(target))
            converted = read_mesh(target).elements
            self.assertEqual(
                tuple(element.t_id for element in converted),
                expected_targets,
            )
            for source_t_id, element in zip(source_types, converted):
                self.assertTrue(
                    all(
                        order == 2
                        for face_orders in element.orders_per_face
                        for order in face_orders
                    )
                )
                if source_t_id in (16, 510, 511):
                    self.assertEqual(element.edges_per_face, (4,) * 6)
                    self.assertEqual(element.nodes_per_face, (8,) * 6)
                else:
                    self.assertEqual(element.edges_per_face, (4, 4, 4, 3, 3))
                    self.assertEqual(element.nodes_per_face, (8, 8, 8, 6, 6))


if __name__ == "__main__":
    unittest.main()
