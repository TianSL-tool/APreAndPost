import tempfile
import unittest
from pathlib import Path

from pre_group.ui_scale_all_nodes_by_center_node import scale_all_nodes_by_center_node


class ScaleAllNodesByCenterNodeTests(unittest.TestCase):
    def test_scales_all_nodes_about_center_node(self):
        grid_text = (
            "node\n"
            "1 0 0 0 0 0 0 0 0 0 0\n"
            "2 1 2 3 1 0 1 0 1 0 1\n"
            "3 3 2 1 0 1 0 1 0 1 0\n"
            "4 -1 0 2 1 1 1 0 0 0 0\n"
            "5 0 1 0 0 0 0 0 0 0 0\n"
            "6 1 1 0 0 0 0 0 0 0 0\n"
            "7 1 0 1 0 0 0 0 0 0 0\n"
            "8 0 1 1 0 0 0 0 0 0 0\n"
            "end node\n"
            "element\n"
            "101 6 12 23 34 45 1 2 3 4 5 6 7 8\n"
            "end element\n"
        )
        control_text = (
            "CENTER_NODE_ID = 2\n"
            "SCALE_X = 2\n"
            "SCALE_Y = 0.5\n"
            "SCALE_Z = 1\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.dat"
            control_path = Path(directory) / "control.dat"
            output_path = Path(directory) / "output.dat"
            input_path.write_text(grid_text, encoding="utf-8")
            control_path.write_text(control_text, encoding="utf-8")

            result = scale_all_nodes_by_center_node(
                control_path,
                input_path,
                output_path,
            )

            self.assertEqual(result[0:3], (8, 1, 2))
            output_lines = output_path.read_text(encoding="utf-8").splitlines()
            node_lines = output_lines[1:output_lines.index("end node")]
            scaled = {
                int(parts[0]): tuple(map(float, parts[1:4]))
                for parts in (line.split() for line in node_lines)
            }

            self.assertEqual(scaled[2], (1.0, 2.0, 3.0))
            self.assertEqual(scaled[1], (-1.0, 1.0, 0.0))
            self.assertEqual(scaled[3], (5.0, 2.0, 1.0))

    def test_rejects_same_input_and_output(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.dat"
            control_path = Path(directory) / "control.dat"
            input_path.write_text("", encoding="utf-8")
            control_path.write_text("CENTER_NODE_ID = 1\nSCALE_FACTOR = 1\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "输出文件不能与输入网格文件相同"):
                scale_all_nodes_by_center_node(control_path, input_path, input_path)


if __name__ == "__main__":
    unittest.main()
