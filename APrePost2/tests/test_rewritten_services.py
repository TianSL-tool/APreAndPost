from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

from aprepost2.domain.element import Polyhedron, PolygonContact
from aprepost2.io.mesh_io import read_mesh
from aprepost2.services.inversion import inversion_postprocess
from aprepost2.services.mesh_cutting import cut_mesh
from aprepost2.services.restart_export import export_restart_element_gauss_data
from aprepost2.services.hdf5_material_filter import delete_hdf5_data_by_element_ids
from aprepost2.services.result_reader import _solid_2d_derived, read_hdf5_results


CUBE_MESH = """node
1 0 0 0 0 0 0 0 0 0 0
2 1 0 0 0 0 0 0 0 0 0
3 1 1 0 0 0 0 0 0 0 0
4 0 1 0 0 0 0 0 0 0 0
5 0 0 1 0 0 0 0 0 0 0
6 1 0 1 0 0 0 0 0 0 0
7 1 1 1 0 0 0 0 0 0 0
8 0 1 1 0 0 0 0 0 0 0
end node
element
1 6 10 1 0 0 1 2 3 4 5 6 7 8
end element
"""

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
1 6 10 1 0 0 1 2 3 4 5 6 7 8
2 6 10 1 0 0 2 9 10 3 6 11 12 7
end element
"""


class RewrittenServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.mesh = self.root / "cube.dat"
        self.mesh.write_text(CUBE_MESH, encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_native_convex_polyhedron_cut(self):
        control = self.root / "cut.txt"
        control.write_text(
            "1.0\n"
            "1\n"
            "0\n"
            "-10 10 -10 10 -10 10\n"
            "0.5 0 0\n"
            "0.5 1 0\n"
            "0.5 0 1\n"
            "0\n",
            encoding="utf-8",
        )
        output = self.root / "cut.dat"
        result = cut_mesh(str(self.mesh), str(control), str(output), 1e-9)
        mesh = read_mesh(output)
        self.assertEqual(result.metrics["cut_elements"], 1)
        self.assertEqual(result.metrics["new_nodes"], 4)
        self.assertTrue(any("筛选与切割" in line for line in result.log_lines))
        self.assertTrue(any("写出网格" in line for line in result.log_lines))
        self.assertEqual(len(mesh.elements), 2)
        self.assertTrue(all(isinstance(e, Polyhedron) for e in mesh.elements))
        self.assertEqual([element.t_id for element in mesh.elements], [57, 57])
        self.assertTrue(
            all(element.faces_are_oriented_outward(mesh.node_map) for element in mesh.elements)
        )
        centers = sorted(element.center(mesh.node_map)[0] for element in mesh.elements)
        np.testing.assert_allclose(centers, [0.25, 0.75])
        shared = set(mesh.elements[0].node_ids) & set(mesh.elements[1].node_ids)
        self.assertEqual(len(shared), 4)

    def test_native_cut_allows_slightly_warped_hex_faces(self):
        warped_mesh = self.root / "warped_cube.dat"
        warped_mesh.write_text(
            CUBE_MESH.replace(
                "7 1 1 1 0 0 0 0 0 0 0",
                "7 1 1 1.05 0 0 0 0 0 0 0",
            ),
            encoding="utf-8",
        )
        control = self.root / "warped_cut.txt"
        control.write_text(
            "1.0\n"
            "1\n"
            "0\n"
            "-10 10 -10 10 -10 10\n"
            "0.5 0 0\n"
            "0.5 1 0\n"
            "0.5 0 1\n"
            "0\n",
            encoding="utf-8",
        )
        output = self.root / "warped_cut.dat"
        result = cut_mesh(str(warped_mesh), str(control), str(output), 1e-9)
        mesh = read_mesh(output)
        self.assertEqual(result.metrics["cut_elements"], 1)
        self.assertEqual(len(mesh.elements), 2)

    def test_cut_defaults_to_boundary_node_insertion(self):
        two_cube_mesh = self.root / "two_cubes.dat"
        two_cube_mesh.write_text(TWO_CUBE_MESH, encoding="utf-8")
        control = self.root / "default_boundary_cut.txt"
        control.write_text(
            "1.0\n"
            "1\n"
            "0\n"
            "-10 1.0 -10 10 -10 10\n"
            "0 0.5 0\n"
            "1 0.5 0\n"
            "0 0.5 1\n",
            encoding="utf-8",
        )
        output = self.root / "default_boundary_cut.dat"
        result = cut_mesh(str(two_cube_mesh), str(control), str(output), 1e-9)
        mesh = read_mesh(output)
        self.assertEqual(result.metrics["cut_elements"], 1)
        self.assertEqual(len(mesh.elements), 3)
        neighbor = mesh.elements[-1]
        self.assertIsInstance(neighbor, Polyhedron)
        self.assertEqual(neighbor.t_id, 57)
        self.assertEqual(sorted(len(face) for face in neighbor.faces()), [4, 4, 4, 4, 4, 5, 5])
        self.assertTrue(
            all(
                element.faces_are_oriented_outward(mesh.node_map)
                for element in mesh.elements
                if isinstance(element, Polyhedron)
            )
        )
        inserted_on_neighbor_edges = {
            node_id
            for node_id in neighbor.node_ids
            if node_id > 12
            and abs(mesh.node_map[node_id].x - 1.0) <= 1e-9
            and abs(mesh.node_map[node_id].y - 0.5) <= 1e-9
        }
        self.assertEqual(len(inserted_on_neighbor_edges), 2)

    def test_native_interface_element_cut_preserves_interface_type(self):
        interface_mesh = self.root / "interface.dat"
        interface_mesh.write_text(CUBE_MESH.replace("1 6 10", "1 9 10"), encoding="utf-8")
        control = self.root / "interface_cut.txt"
        control.write_text(
            "1\n1\n0\n-10 10 -10 10 -10 10\n"
            "0.5 0 0\n0.5 1 0\n0.5 0 1\n0\n",
            encoding="utf-8",
        )
        output = self.root / "interface_cut.dat"
        cut_mesh(str(interface_mesh), str(control), str(output), 1e-9)
        mesh = read_mesh(output)
        self.assertTrue(all(isinstance(e, PolygonContact) for e in mesh.elements))
        self.assertEqual([element.t_id for element in mesh.elements], [60, 60])
        self.assertTrue(all(len(element.node_ids) % 2 == 0 for element in mesh.elements))

    def test_native_hdf5_result_reader(self):
        hdf5 = self.root / "result.h5"
        with h5py.File(hdf5, "w") as file:
            frames = file.create_group("frames")
            for step, multiplier in (("1", 1.0), ("2", 2.0)):
                frame = frames.create_group(step)
                if step == "1":
                    topology = frame.create_group("new_topology")
                    topology.create_dataset("node_ids", data=np.arange(1, 9))
                node_vars = frame.create_group("node_vars")
                displacement = np.zeros((8, 3))
                displacement[0] = [multiplier, 0, 0]
                displacement[1] = [0.25 * multiplier, 0, 0]
                node_vars.create_dataset("displacement", data=displacement)
                node_vars.create_dataset("poressure", data=np.arange(8) * multiplier)
                part = frame.create_group("parts").create_group("solid")
                if step == "1":
                    part.create_dataset("elem_ids", data=[1])
                variables = part.create_group("elem_vars")
                variables.create_dataset(
                    "stress", data=[[-1, -2, -3, 0, 0, 0]]
                )
                variables.create_dataset(
                    "strain", data=[[0.01, 0.02, 0.03, 0, 0, 0]]
                )
        control = self.root / "result_control.txt"
        control.write_text(
            "output node number = 1\n"
            "1\n"
            "output element number = 1\n"
            "1\n"
            "output step number = 1\n"
            "2\n"
            "base node = 2\n"
            "podu = 0\n"
            "initial stress = 1\n"
            "initial strain = 1\n",
            encoding="utf-8",
        )
        prefix = self.root / "output"
        result = read_hdf5_results(
            str(control), str(hdf5), str(prefix), str(self.mesh)
        )
        self.assertEqual(result.metrics, {"nodes": 2, "elements": 1})
        node_frame = pd.read_excel(
            self.root / "output_node_schedule.xlsx", sheet_name="1"
        )
        np.testing.assert_allclose(node_frame["dispx"], [0.75, 1.5])
        element_frame = pd.read_excel(
            self.root / "output_element_schedule.xlsx", sheet_name="1"
        )
        self.assertIn("p", element_frame.columns)
        self.assertIn("dynamic_shear_strain", element_frame.columns)
        self.assertTrue(
            (self.root / "output_details" / "step_2_node_data.txt").is_file()
        )

    def test_two_dimensional_derived_stress_strain(self):
        derived = _solid_2d_derived(
            np.asarray([-1.0, -2.0, -3.0, 0.0]),
            np.asarray([-0.01, -0.02, 0.0]),
            0.0,
        )
        self.assertAlmostEqual(derived[0], 2.0)
        self.assertAlmostEqual(derived[1], np.sqrt(3.0))
        np.testing.assert_allclose(derived[2:5], [3.0, 2.0, 1.0])
        self.assertAlmostEqual(derived[8], 0.03)

    def test_restart_gauss_point_export_uses_element_info_layout(self):
        hdf5 = self.root / "restart.h5"
        with h5py.File(hdf5, "w") as file:
            group = file.create_group("output_for_restart").create_group("57")
            group.attrs["dynamic"] = [1]
            group.attrs["time"] = [12.5]
            group.create_dataset(
                "element_info",
                data=np.asarray(
                    [
                        [10, 5, 2, 3, 2, 4],
                        [20, 6, 1, 6, 6, 2],
                    ],
                    dtype=np.int32,
                ),
            )
            group.create_dataset("stress", data=np.arange(12, dtype=np.float64))
            group.create_dataset("strain", data=np.arange(100, 110, dtype=np.float64))
            group.create_dataset(
                "constitutive_variables",
                data=np.arange(200, 210, dtype=np.float64),
            )

        output = self.root / "restart_export.xlsx"
        result = export_restart_element_gauss_data(
            str(hdf5), "57", "20, 10", str(output)
        )
        self.assertEqual(result.metrics, {"elements": 2, "gauss_points": 3})
        frame = pd.read_excel(output, sheet_name="gauss_point_data")
        self.assertEqual(frame["element_id"].tolist(), [10, 10, 20])
        self.assertEqual(frame["gauss_point"].tolist(), [1, 2, 1])
        np.testing.assert_allclose(frame.loc[0, ["stress_1", "stress_2", "stress_3"]], [0, 1, 2])
        np.testing.assert_allclose(frame.loc[1, ["strain_1", "strain_2"]], [102, 103])
        np.testing.assert_allclose(frame.loc[2, ["state_1", "state_2"]], [208, 209])
        summary = pd.read_excel(output, sheet_name="selected_elements")
        self.assertEqual(summary["element_id"].tolist(), [10, 20])
        self.assertEqual(summary["material_type"].tolist(), [5, 6])

    def test_restart_gauss_point_export_skips_missing_optional_dataset(self):
        hdf5 = self.root / "restart_without_state.h5"
        with h5py.File(hdf5, "w") as file:
            group = file.create_group("output_for_restart").create_group("57")
            group.create_dataset(
                "element_info",
                data=np.asarray([[10, 5, 2, 2, 1, 4]], dtype=np.int32),
            )
            group.create_dataset("stress", data=np.asarray([1.0, 2.0, 3.0, 4.0]))
            group.create_dataset("strain", data=np.asarray([10.0, 11.0]))

        output = self.root / "restart_without_state.xlsx"
        result = export_restart_element_gauss_data(str(hdf5), "57", "10", str(output))

        self.assertEqual(result.metrics, {"elements": 1, "gauss_points": 2})
        frame = pd.read_excel(output, sheet_name="gauss_point_data")
        self.assertEqual(frame["element_id"].tolist(), [10, 10])
        self.assertEqual(frame["state_variables"].tolist(), [4, 4])
        self.assertNotIn("state_1", frame.columns)
        np.testing.assert_allclose(frame.loc[:, ["stress_1", "stress_2"]], [[1, 2], [3, 4]])
        np.testing.assert_allclose(frame["strain_1"], [10, 11])

    def test_delete_hdf5_data_by_element_ids_keeps_gauss_point_alignment(self):
        hdf5 = self.root / "initial.h5"
        with h5py.File(hdf5, "w") as file:
            file.attrs["case"] = "two-order"
            group = file.create_group("output_for_initial_condition").create_group("100")
            group.attrs["time"] = [100.0]
            info = group.create_dataset(
                "element_info",
                data=np.asarray(
                    [
                        [10, 1, 1, 2, 1, 0],
                        [20, 2, 2, 3, 2, 1],
                        [30, 1, 1, 1, 3, 2],
                    ],
                    dtype=np.int32,
                ),
            )
            info.attrs["columns"] = 6
            group.create_dataset(
                "stress", data=np.arange(9, dtype=np.float64), compression="gzip"
            )
            group.create_dataset("strain", data=np.arange(100, 108, dtype=np.float64))
            group.create_dataset(
                "constitutive_variables",
                data=np.arange(200, 204, dtype=np.float64),
            )
            file.create_group("unrelated").create_dataset("values", data=[7, 8])

        element_ids = self.root / "element_ids.txt"
        element_ids.write_text("2\n10\n30\n", encoding="utf-8")
        output = self.root / "initial_without_selected_elements.h5"
        result = delete_hdf5_data_by_element_ids(
            str(hdf5), "auto", str(element_ids), str(output)
        )
        self.assertEqual(result.metrics["deleted_elements"], 2)
        self.assertEqual(result.metrics["deleted_gauss_points"], 2)
        self.assertEqual(result.metrics["remaining_elements"], 1)

        with h5py.File(output, "r") as file:
            self.assertEqual(file.attrs["case"], "two-order")
            np.testing.assert_array_equal(file["unrelated/values"][...], [7, 8])
            group = file["output_for_initial_condition/100"]
            np.testing.assert_array_equal(
                group["element_info"][...],
                np.asarray([[20, 2, 2, 3, 2, 1]], dtype=np.int32),
            )
            np.testing.assert_array_equal(group["stress"][...], np.arange(2, 8))
            np.testing.assert_array_equal(group["strain"][...], np.arange(101, 105))
            np.testing.assert_array_equal(
                group["constitutive_variables"][...], np.arange(200, 202)
            )
            self.assertEqual(group["element_info"].attrs["columns"], 6)
            self.assertEqual(group["stress"].compression, "gzip")
            self.assertEqual(group.attrs["time"][0], 100.0)

    def test_delete_hdf5_data_by_element_ids_rejects_missing_or_all_elements(self):
        hdf5 = self.root / "restart_filter.h5"
        with h5py.File(hdf5, "w") as file:
            group = file.create_group("output_for_restart").create_group("57")
            group.create_dataset(
                "element_info",
                data=np.asarray([[10, 5, 1, 1, 1, 1]], dtype=np.int32),
            )
            group.create_dataset("stress", data=[1.0])
            group.create_dataset("strain", data=[2.0])
            group.create_dataset("constitutive_variables", data=[3.0])

        missing_ids = self.root / "missing_ids.txt"
        missing_ids.write_text("99\n", encoding="utf-8")
        all_ids = self.root / "all_ids.txt"
        all_ids.write_text("10\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "单元号未在 element_info 中找到"):
            delete_hdf5_data_by_element_ids(
                str(hdf5),
                "output_for_restart/57",
                str(missing_ids),
                str(self.root / "missing.h5"),
            )
        with self.assertRaisesRegex(ValueError, "无剩余单元"):
            delete_hdf5_data_by_element_ids(
                str(hdf5), "auto", str(all_ids), str(self.root / "empty.h5")
            )
        self.assertFalse((self.root / "missing.h5").exists())
        self.assertFalse((self.root / "empty.h5").exists())

    def test_native_inversion_pipeline(self):
        first_time = pd.Timestamp("2020-01-01")
        second_time = pd.Timestamp("2020-01-11")
        measurement_book = self.root / "measurement.xlsx"
        setup = pd.DataFrame(None, index=range(4), columns=range(5), dtype=object)
        setup.iat[0, 1] = 1
        setup.iat[0, 4] = "L"
        setup.iat[1, 0] = "Data"
        setup.iat[2, 0] = 101
        setup.iat[3, 0] = first_time
        measured = pd.DataFrame(
            {"time": [first_time, second_time], "101": [0.0, 10.0]}
        )
        with pd.ExcelWriter(measurement_book, engine="openpyxl") as writer:
            setup.to_excel(writer, sheet_name="setup", header=False, index=False)
            measured.to_excel(writer, sheet_name="Data", index=False)

        control_book = self.root / "control.xlsx"
        control = pd.DataFrame(None, index=range(2), columns=range(9), dtype=object)
        control.iat[0, 1] = 1
        control.iat[0, 2] = "L"
        control.iat[0, 3] = 101
        control.iat[0, 4] = 1
        control.iloc[0, 5:9] = [100, 200, 300, 0]
        control.iat[0, 8] = "node"
        control.iat[1, 0] = "scenario"

        scenario = pd.DataFrame(
            None, index=range(18), columns=range(10), dtype=object
        )
        scenario.iat[0, 1] = "condition"
        scenario.iat[0, 4] = 2
        scenario.iat[1, 3] = 2
        scenario.iat[1, 5] = first_time
        scenario.iat[1, 6] = 1
        scenario.iat[2, 1] = 1
        scenario.iat[2, 3] = first_time
        scenario.iat[2, 5] = second_time
        scenario.iat[2, 6] = 2
        scenario.iat[3, 1] = 0
        scenario.iat[3, 3] = second_time
        scenario.iat[4, 1] = 1.0
        scenario.iat[5, 1] = 1.0
        scenario.iat[6, 0] = measurement_book.name
        scenario.iat[7, 1] = 0
        scenario.iat[8, 1] = 1
        scenario.iat[9, 1] = 1
        scenario.iat[10, 1] = -1
        scenario.iat[11, 1] = 1000
        scenario.iat[12, 1] = -1
        scenario.iat[13, 1] = 0
        scenario.iat[14, 1] = -3
        scenario.iat[15, 1] = 4
        scenario.iat[16, 1] = 1
        scenario.iat[17, 1] = 0
        with pd.ExcelWriter(control_book, engine="openpyxl") as writer:
            control.to_excel(writer, sheet_name="control", header=False, index=False)
            scenario.to_excel(writer, sheet_name="scenario", header=False, index=False)

        pd.DataFrame(
            {"step": [1, 2], "dispx": [0.0, 0.01], "dispy": [0.0, 0.0]}
        ).to_csv(self.root / "1.node", sep="\t", index=False)
        result = inversion_postprocess(str(control_book), 1, 3)
        self.assertEqual(result.metrics["scenarios"], 1)
        self.assertTrue((self.root / "outmeasurement.xlsx").is_file())
        self.assertTrue((self.root / "out2measurement.xlsx").is_file())

    def test_inversion_accepts_legacy_shifted_label_layout(self):
        first_time = pd.Timestamp("2020-01-01")
        second_time = pd.Timestamp("2020-01-11")
        measurement_book = self.root / "legacy_measurement.xlsx"
        setup = pd.DataFrame(None, index=range(4), columns=range(5), dtype=object)
        setup.iat[0, 1] = 1
        setup.iat[0, 2] = "Label"
        setup.iat[0, 3] = "CH"
        setup.iat[1, 0] = "Data"
        setup.iat[2, 0] = 101
        setup.iat[3, 0] = first_time
        measured = pd.DataFrame(
            {"time": [first_time, second_time], "101": [0.0, 10.0]}
        )
        with pd.ExcelWriter(measurement_book, engine="openpyxl") as writer:
            setup.to_excel(writer, sheet_name="control", header=False, index=False)
            measured.to_excel(writer, sheet_name="Data", index=False)

        control_book = self.root / "legacy_control.xlsx"
        control = pd.DataFrame(None, index=range(2), columns=range(9), dtype=object)
        control.iat[0, 1] = 1
        control.iloc[0, 2:9] = ["CH", 101, 1, 100, 200, 300, "node"]
        control.iat[1, 0] = "scenario"
        scenario = pd.DataFrame(None, index=range(18), columns=range(10), dtype=object)
        scenario.iat[0, 1] = "condition"
        scenario.iat[0, 4] = 2
        scenario.iat[1, 3] = 2
        scenario.iloc[1, 5:7] = [first_time, 1]
        scenario.iloc[2, [1, 3, 5, 6]] = [1, first_time, second_time, 2]
        scenario.iloc[3, [1, 3]] = [0, second_time]
        scenario.iloc[4:18, 1] = [1, 1, None, 0, 1, 1, -1, 1000, -1, 0, -3, 4, 1, 0]
        scenario.iat[6, 0] = measurement_book.name
        with pd.ExcelWriter(control_book, engine="openpyxl") as writer:
            control.to_excel(writer, sheet_name="control", header=False, index=False)
            scenario.to_excel(writer, sheet_name="scenario", header=False, index=False)
        pd.DataFrame(
            {"step": [1, 2], "dispx": [0.0, 0.01], "dispy": [0.0, 0.0]}
        ).to_csv(self.root / "1.node", sep="\t", index=False)

        result = inversion_postprocess(str(control_book), 1, 3)
        self.assertTrue(any("1 个测点" in line for line in result.log_lines))
        summary = pd.read_excel(self.root / "outlegacy_measurement.xlsx", sheet_name="Data")
        self.assertEqual(summary.iloc[0, 1], 100)
        self.assertEqual(summary.iloc[1, 1], 200)
        self.assertEqual(summary.iloc[2, 1], 300)


if __name__ == "__main__":
    unittest.main()
