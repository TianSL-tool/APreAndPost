from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np

from aprepost2.domain.element import QuadSolid2D, Slip2D
from aprepost2.io.mesh_io import read_mesh
from aprepost2.services.mesh_section import (
    _solid_section_payload,
    _solid_section_type,
    extract_mesh_section,
)


TWO_CUBE_MESH = """node
1 0 0 0 0 0 0 0 0 0 0
2 1 0 0 0 0 0 0 0 0 0
3 1 1 0 0 0 0 0 0 0 0
4 0 1 0 0 0 0 0 0 0 0
5 0 0 1 0 0 0 0 0 0 0
6 1 0 1 0 0 0 0 0 0 0
7 1 1 1 0 0 0 0 0 0 0
8 0 1 1 0 0 0 0 0 0 0
9 2 0 0 0 0 0 0 0 0 0
10 2 1 0 0 0 0 0 0 0 0
11 2 0 1 0 0 0 0 0 0 0
12 2 1 1 0 0 0 0 0 0 0
end node
element
1 6 10 1 20 30 1 2 3 4 5 6 7 8
2 6 11 2 21 31 2 9 10 3 6 11 12 7
end element
"""


CONTACT_MESH = """node
1 0 0 0 0 0 0 0 0 0 0
2 1 0 0 0 0 0 0 0 0 0
3 1 1 0 0 0 0 0 0 0 0
4 0 1 0 0 0 0 0 0 0 0
5 0 0 0 0 0 0 0 0 0 0
6 1 0 0 0 0 0 0 0 0 0
7 1 1 0 0 0 0 0 0 0 0
8 0 1 0 0 0 0 0 0 0 0
end node
element
1 9 10 2 20 30 1 2 3 4 5 6 7 8
end element
"""


class MeshSectionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / "two_cubes.dat"
        self.source.write_text(TWO_CUBE_MESH, encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def extract(self, output_name: str, **overrides):
        arguments = {
            "input_path": str(self.source),
            "output_path": str(self.root / output_name),
            "origin_x": 0.5,
            "origin_y": 0.0,
            "origin_z": 0.0,
            "normal_x": 1.0,
            "normal_y": 0.0,
            "normal_z": 0.0,
            "material_ids": "all",
            "tolerance": 1.0e-9,
        }
        arguments.update(overrides)
        result = extract_mesh_section(**arguments)
        return result, read_mesh(arguments["output_path"])

    def test_extracts_polygon_and_preserves_source_attributes(self):
        result, section = self.extract("section.dat")
        self.assertEqual(result.metrics["section_elements"], 1)
        self.assertEqual(result.metrics["new_nodes"], 4)
        self.assertEqual(result.metrics["section_quads"], 1)
        self.assertEqual(len(section.nodes), 4)
        element = section.elements[0]
        self.assertIsInstance(element, QuadSolid2D)
        self.assertEqual(element.t_id, 1)
        self.assertEqual(
            (element.e_id, element.t_id, element.c_id, element.m_id,
             element.d_id, element.f_id),
            (1, 1, 10, 1, 20, 30),
        )
        self.assertTrue(all(abs(node.x - 0.5) <= 1.0e-9 for node in section.nodes))
        points = np.asarray(
            [section.node_map[node_id].coordinates for node_id in element.node_ids]
        )
        area_vector = sum(
            np.cross(point, points[(index + 1) % len(points)])
            for index, point in enumerate(points)
        )
        self.assertGreater(area_vector[0], 0.0)

    def test_shared_coplanar_face_is_written_once_with_existing_nodes(self):
        result, section = self.extract("shared_face.dat", origin_x=1.0)
        self.assertEqual(result.metrics["section_elements"], 1)
        self.assertEqual(result.metrics["duplicate_sections"], 1)
        self.assertEqual(result.metrics["new_nodes"], 0)
        self.assertEqual(set(section.elements[0].node_ids), {2, 3, 6, 7})

    def test_material_filter_limits_source_elements(self):
        result, section = self.extract(
            "material_2.dat", origin_x=1.5, material_ids="2"
        )
        self.assertEqual(result.metrics["section_elements"], 1)
        self.assertEqual(section.elements[0].m_id, 2)
        self.assertEqual(section.elements[0].e_id, 2)


    def test_hex_contact_extracts_as_layered_2d_contact(self):
        mappings = ((9, 4), (902, 700), (903, 777))
        for source_type, target_type in mappings:
            with self.subTest(source_type=source_type):
                source = self.root / f"contact_{source_type}.dat"
                source.write_text(
                    CONTACT_MESH.replace("1 9 10", f"1 {source_type} 10"),
                    encoding="utf-8",
                )
                output = self.root / f"contact_section_{source_type}.dat"
                result = extract_mesh_section(
                    str(source),
                    str(output),
                    0.5,
                    0.0,
                    0.0,
                    1.0,
                    0.0,
                    0.0,
                    "all",
                    1.0e-9,
                )
                section = read_mesh(output)
                self.assertEqual(result.metrics["section_contacts"], 1)
                self.assertEqual(result.metrics["new_nodes"], 4)
                self.assertEqual(len(section.elements), 1)
                element = section.elements[0]
                self.assertIsInstance(element, Slip2D)
                self.assertEqual(element.t_id, target_type)
                self.assertEqual((element.e_id, element.c_id, element.m_id), (1, 10, 2))
                bottom = element.node_ids[:2]
                top = element.node_ids[2:]
                self.assertTrue(set(bottom).isdisjoint(top))
                bottom_points = [section.node_map[node_id].coordinates for node_id in bottom]
                top_points = [section.node_map[node_id].coordinates for node_id in top]
                self.assertEqual(bottom_points, list(reversed(top_points)))

    def test_near_plane_contact_vertex_does_not_create_duplicate_intersection(self):
        lines = CONTACT_MESH.splitlines()
        z_coordinates = (0.00127612, -5.00361, -5.00559, 0.00000023,
                         0.0, -5.00334, -5.00559, 0.0)
        for node_index, z_coordinate in enumerate(z_coordinates, 1):
            values = lines[node_index].split()
            values[3] = str(z_coordinate)
            lines[node_index] = " ".join(values)
        source = self.root / "near_plane_contact.dat"
        source.write_text("\n".join(lines) + "\n", encoding="utf-8")
        output = self.root / "near_plane_section.dat"
        result = extract_mesh_section(
            str(source),
            str(output),
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            1.0,
            "all",
            1.0e-6,
        )
        section = read_mesh(output)
        self.assertEqual(result.metrics["section_contacts"], 1)
        self.assertIn(1, section.element_map)
        self.assertEqual(section.element_map[1].t_id, 4)



    def test_three_node_section_uses_degenerate_quad_payload(self):
        self.assertEqual(_solid_section_payload((10, 20, 30)), (10, 20, 30, 30))
        self.assertEqual(_solid_section_type(6, 3), 1)
        self.assertEqual(_solid_section_type(5, 3), 2)
        self.assertEqual(_solid_section_type(500, 3), 222)

    def test_rejects_zero_normal_without_writing_output(self):
        output = self.root / "invalid.dat"
        with self.assertRaisesRegex(ValueError, "法向量"):
            extract_mesh_section(
                str(self.source), str(output), 0, 0, 0, 0, 0, 0, "all", 1e-9
            )
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
