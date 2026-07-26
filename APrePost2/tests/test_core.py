from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import h5py

from aprepost2.domain.element import Hexahedron, PolygonSolid2D, Polyhedron, QuadSolid2D
from aprepost2.io.mesh_io import read_mesh
from aprepost2.services.hdf5 import merge_hdf5
from aprepost2.services.mesh_operations import (
    add_pore_constraints,
    change_all_fill_ids,
    change_element_types,
    convert_element_types_by_material,
    export_elements_by_bounds,
    merge_close_nodes,
    offset_mesh_ids,
    remap_fill_ids,
    remap_material_ids,
    scale_all_nodes_by_center_node,
    scale_coordinates,
)


MESH_TEXT = """node
       1     0.0000000000     0.0000000000     0.0000000000 0 0 0 0 0 0 0
       2     1.0000000000     0.0000000000     0.0000000000 1 0 0 0 0 0 0
       3     0.0000000000     1.0000000000     0.0000000000 0 1 0 0 0 0 0
       4     0.0000000000     0.0000000000     1.0000000000 0 0 1 0 0 0 0
       5     2.0000000000     0.0000000000     0.0000000000 0 0 0 0 0 0 0
end node
element
       1 6 10 1 0 0 1 2 3 4 4 4 4 4
       2 6 20 2 0 0 1 4 5 5 5 5 5 5
end element
"""


class CoreServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.mesh_path = self.root / "mesh.dat"
        self.mesh_path.write_text(MESH_TEXT, encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def _control(self, name: str, content: str) -> Path:
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_mesh_reader_preserves_engineering_fields_and_connectivity(self):
        mesh = read_mesh(self.mesh_path)
        self.assertEqual([node.node_id for node in mesh.nodes], [1, 2, 3, 4, 5])
        self.assertEqual(mesh.node_map[2].ux, 1)
        self.assertIsInstance(mesh.elements[0], Hexahedron)
        self.assertEqual(mesh.elements[0].node_ids, (1, 2, 3, 4, 4, 4, 4, 4))
        self.assertEqual(
            (
                mesh.elements[0].e_id,
                mesh.elements[0].t_id,
                mesh.elements[0].c_id,
                mesh.elements[0].m_id,
            ),
            (1, 6, 10, 1),
        )

    def test_polyhedron_topology_round_trip(self):
        polyhedron = self.root / "polyhedron.dat"
        polyhedron.write_text(
            MESH_TEXT.split("element", 1)[0]
            + "element\n"
            + "1 57 10 1 0 0 4 3 3 3 3 1 2 3 1 4 2 2 4 3 3 4 1\n"
            + "end element\n",
            encoding="utf-8",
        )
        mesh = read_mesh(polyhedron)
        self.assertIsInstance(mesh.elements[0], Polyhedron)
        self.assertEqual(len(mesh.elements[0].faces()), 4)
        from aprepost2.io.mesh_io import write_mesh

        output = self.root / "polyhedron_out.dat"
        write_mesh(output, mesh)
        reread = read_mesh(output)
        self.assertEqual(reread.elements[0].faces(), mesh.elements[0].faces())

    def test_material_and_fill_mapping_change_only_target_fields(self):
        material_control = self._control("material.txt", "1\n1 9\n")
        material_output = self.root / "material.dat"
        remap_material_ids(
            str(self.mesh_path), str(material_control), str(material_output)
        )
        material_mesh = read_mesh(material_output)
        self.assertEqual([element.m_id for element in material_mesh.elements], [9, 2])
        self.assertEqual([element.c_id for element in material_mesh.elements], [10, 20])

        fill_control = self._control("fill.txt", "2\n10 100\n20 200\n")
        fill_output = self.root / "fill.dat"
        remap_fill_ids(str(self.mesh_path), str(fill_control), str(fill_output))
        fill_mesh = read_mesh(fill_output)
        self.assertEqual([element.c_id for element in fill_mesh.elements], [100, 200])
        self.assertEqual([element.m_id for element in fill_mesh.elements], [1, 2])

    def test_all_fill_and_element_type_conversion(self):
        fill_output = self.root / "all_fill.dat"
        result = change_all_fill_ids(str(self.mesh_path), str(fill_output), 7)
        self.assertEqual(result.metrics["changed"], 2)
        self.assertEqual(
            [element.c_id for element in read_mesh(fill_output).elements], [7, 7]
        )

        type_control = self._control("type.txt", "1\n1\n1\n6 61\n")
        type_output = self.root / "type.dat"
        result = change_element_types(
            str(self.mesh_path), str(type_control), str(type_output)
        )
        self.assertEqual(result.metrics["changed"], 1)
        converted = read_mesh(type_output)
        self.assertIsInstance(converted.elements[0], Hexahedron)
        self.assertIsInstance(converted.elements[1], Hexahedron)
        self.assertEqual(
            [element.t_id for element in converted.elements], [61, 6]
        )

        unsupported = self._control("unsupported.txt", "1\n1\n1\n6 999\n")
        with self.assertRaisesRegex(ValueError, "尚未注册安全"):
            change_element_types(
                str(self.mesh_path), str(unsupported), str(self.root / "bad.dat")
            )

    def test_material_scoped_topology_conversion(self):
        source = self.root / "quad_mesh.dat"
        source.write_text(
            "node\n"
            "1 0 0 0 0 0 0 0 0 0 0\n"
            "2 1 0 0 0 0 0 0 0 0 0\n"
            "3 1 1 0 0 0 0 0 0 0 0\n"
            "4 0 1 0 0 0 0 0 0 0 0\n"
            "5 2 0 0 0 0 0 0 0 0 0\n"
            "6 2 1 0 0 0 0 0 0 0 0\n"
            "end node\n"
            "element\n"
            "1 1 10 1 0 0 1 2 3 4\n"
            "2 1 20 2 0 0 2 5 6 3\n"
            "end element\n",
            encoding="utf-8",
        )
        control = self._control("topology.txt", "1\n1\n1\n1 44\n")
        output = self.root / "topology.dat"
        result = convert_element_types_by_material(str(source), str(control), str(output))
        mesh = read_mesh(output)
        self.assertEqual(result.metrics["changed"], 1)
        self.assertIsInstance(mesh.elements[0], PolygonSolid2D)
        self.assertIsInstance(mesh.elements[1], QuadSolid2D)
        self.assertEqual(mesh.elements[0].t_id, 44)
        self.assertEqual(mesh.elements[0].m_id, 1)
        self.assertEqual(mesh.elements[0].node_ids, (1, 2, 3, 4))
        self.assertEqual(mesh.elements[1].t_id, 1)

    def test_pore_constraints_use_material_adjacency(self):
        control = self._control("pore.txt", "1\n1 2\n")
        output = self.root / "pore.dat"
        result = add_pore_constraints(
            str(self.mesh_path), str(control), str(output)
        )
        mesh = read_mesh(output)
        self.assertEqual(result.metrics["changed"], 2)
        self.assertEqual(
            {node.node_id for node in mesh.nodes if node.press == 1}, {1, 4}
        )

    def test_coordinate_scale_keeps_connectivity(self):
        control = self._control(
            "scale.txt",
            "BASE_POINT = 0, 0, 0\n"
            "SCALE_DIR = x\n"
            "SCALE_RANGE_MIN = 0\n"
            "SCALE_RANGE_MAX = 1\n"
            "SCALE_FACTOR = 2\n",
        )
        output = self.root / "scaled.dat"
        scale_coordinates(str(self.mesh_path), str(control), str(output))
        mesh = read_mesh(output)
        self.assertEqual([node.x for node in mesh.nodes], [0.0, 2.0, 0.0, 0.0, 3.0])
        self.assertEqual(mesh.elements[0].node_ids, (1, 2, 3, 4, 4, 4, 4, 4))

    def test_scale_all_nodes_by_center_node_keeps_connectivity(self):
        control = self._control(
            "scale_center_node.txt",
            "CENTER_NODE_ID = 2\n"
            "SCALE_X = 2\n"
            "SCALE_Y = 0.5\n"
            "SCALE_Z = 1\n",
        )
        output = self.root / "scaled_by_center_node.dat"
        result = scale_all_nodes_by_center_node(
            str(self.mesh_path), str(control), str(output)
        )
        mesh = read_mesh(output)
        self.assertEqual(result.metrics["center_node_id"], 2)
        self.assertEqual(mesh.node_map[2].coordinates, (1.0, 0.0, 0.0))
        self.assertEqual(mesh.node_map[1].coordinates, (-1.0, 0.0, 0.0))
        self.assertEqual(mesh.node_map[3].coordinates, (-1.0, 0.5, 0.0))
        self.assertEqual(mesh.node_map[5].coordinates, (3.0, 0.0, 0.0))
        self.assertEqual(mesh.elements[0].node_ids, (1, 2, 3, 4, 4, 4, 4, 4))

    def test_node_and_element_id_offsets_update_connectivity(self):
        output = self.root / "offset_ids.dat"
        result = offset_mesh_ids(
            str(self.mesh_path),
            node_id_offset=100,
            element_id_offset=200,
            output_path=str(output),
        )
        mesh = read_mesh(output)
        self.assertEqual([node.node_id for node in mesh.nodes], [101, 102, 103, 104, 105])
        self.assertEqual([element.e_id for element in mesh.elements], [201, 202])
        self.assertEqual(
            mesh.elements[0].node_ids,
            (101, 102, 103, 104, 104, 104, 104, 104),
        )
        self.assertEqual(result.metrics["node_id_offset"], 100)
        self.assertEqual(result.metrics["element_id_offset"], 200)

        with self.assertRaisesRegex(ValueError, "节点号偏移后不能小于 0"):
            offset_mesh_ids(
                str(self.mesh_path),
                node_id_offset=-2,
                element_id_offset=0,
                output_path=str(self.root / "invalid_offset.dat"),
            )

    def test_merge_close_nodes_uses_transitive_groups_and_updates_connectivity(self):
        source = self.root / "close_nodes.dat"
        source.write_text(
            "node\n"
            "1 0.00 0 0 0 0 0 0 0 0 0\n"
            "2 0.0625 0 0 1 0 0 0 0 0 0\n"
            "3 0.125 0 0 0 1 0 0 0 0 0\n"
            "4 1.00 0 0 0 0 1 0 0 0 0\n"
            "5 1.125 0 0 0 0 0 0 0 0 0\n"
            "end node\n"
            "element\n"
            "1 44 0 1 0 0 1 2 3 4 5\n"
            "end element\n",
            encoding="utf-8",
        )
        output = self.root / "merged_nodes.dat"
        result = merge_close_nodes(
            str(source), distance_tolerance=0.125, output_path=str(output)
        )
        mesh = read_mesh(output)
        self.assertEqual([node.node_id for node in mesh.nodes], [1, 4, 5])
        self.assertEqual(mesh.elements[0].node_ids, (1, 1, 1, 4, 5))
        self.assertEqual((mesh.node_map[1].ux, mesh.node_map[1].uy), (1, 1))
        self.assertEqual(result.metrics["merged_nodes"], 2)
        self.assertEqual(result.metrics["merge_groups"], 1)
        self.assertEqual(result.metrics["neighbor_pairs"], 2)
        self.assertEqual(result.metrics["collapsed_elements"], 1)

        with self.assertRaisesRegex(ValueError, "合并距离必须"):
            merge_close_nodes(
                str(source), distance_tolerance=0, output_path=str(self.root / "bad.dat")
            )

    def test_range_export_preserves_original_order(self):
        output = self.root / "selected.dat"
        result = export_elements_by_bounds(
            str(self.mesh_path),
            str(output),
            (-1, 0.3, -1, 1, -1, 1),
        )
        mesh = read_mesh(output)
        self.assertEqual(result.metrics["elements"], 1)
        self.assertEqual([element.e_id for element in mesh.elements], [1])
        self.assertEqual([node.node_id for node in mesh.nodes], [1, 2, 3, 4])

    def test_hdf5_merge_replaces_duplicate_frames(self):
        first = self.root / "first.h5"
        second = self.root / "second.h5"
        output = self.root / "merged.h5"
        with h5py.File(first, "w") as file:
            file.create_dataset("metadata", data=[1])
            frames = file.create_group("frames")
            frames.create_dataset("frame_1", data=[1])
        with h5py.File(second, "w") as file:
            frames = file.create_group("frames")
            frames.create_dataset("frame_1", data=[9])
            frames.create_dataset("frame_2", data=[2])
        result = merge_hdf5(str(first), str(second), str(output))
        self.assertEqual(result.metrics["replaced_frames"], 1)
        with h5py.File(output, "r") as file:
            self.assertEqual(file["metadata"][0], 1)
            self.assertEqual(file["frames/frame_1"][0], 9)
            self.assertEqual(file["frames/frame_2"][0], 2)


if __name__ == "__main__":
    unittest.main()
