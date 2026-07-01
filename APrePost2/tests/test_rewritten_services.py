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
        self.assertEqual(len(mesh.elements), 2)
        self.assertTrue(all(isinstance(e, Polyhedron) for e in mesh.elements))
        self.assertEqual([element.t_id for element in mesh.elements], [57, 57])
        centers = sorted(element.center(mesh.node_map)[0] for element in mesh.elements)
        np.testing.assert_allclose(centers, [0.25, 0.75])
        shared = set(mesh.elements[0].node_ids) & set(mesh.elements[1].node_ids)
        self.assertEqual(len(shared), 4)

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


if __name__ == "__main__":
    unittest.main()
