import tempfile
import unittest
from pathlib import Path

from pre_group.ui_export_elements_by_range import export_elements_by_range


class ExportElementsByRangeTests(unittest.TestCase):
    def test_exports_complete_subset_without_changing_input(self):
        node_lines = []
        for node_id in range(1, 17):
            x = 0.0 if node_id <= 8 else 10.0
            y = float((node_id - 1) % 2)
            z = float(((node_id - 1) // 2) % 2)
            node_lines.append(
                f"{node_id} {x} {y} {z} "
                f"{node_id % 2} 0 1 0 1 0 1"
            )
        first_element = "101 6 12 23 34 45 1 2 3 4 5 6 7 8"
        second_element = "202 6 56 67 78 89 9 10 11 12 13 14 15 16"
        grid_text = (
            "node\n" + "\n".join(node_lines) + "\nend node\n"
            "element\n" + first_element + "\n" + second_element +
            "\nend element\n"
        )

        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.dat"
            output_path = Path(directory) / "output.dat"
            input_path.write_text(grid_text, encoding="utf-8")
            original_bytes = input_path.read_bytes()

            node_count, element_count = export_elements_by_range(
                input_path,
                output_path,
                (-0.1, 1.0, -0.1, 1.1, -0.1, 1.1),
            )

            self.assertEqual((node_count, element_count), (8, 1))
            self.assertEqual(input_path.read_bytes(), original_bytes)

            output_lines = output_path.read_text(encoding="utf-8").splitlines()
            element_start = output_lines.index("element")
            element_tokens = output_lines[element_start + 1].split()
            self.assertEqual(element_tokens, first_element.split())
            self.assertEqual(output_lines[element_start + 2], "end element")

            output_node_lines = output_lines[1:output_lines.index("end node")]
            self.assertEqual(len(output_node_lines), 8)
            for source, exported in zip(node_lines[:8], output_node_lines):
                source_tokens = source.split()
                exported_tokens = exported.split()
                self.assertEqual(exported_tokens[0], source_tokens[0])
                self.assertEqual(
                    tuple(map(float, exported_tokens[1:4])),
                    tuple(map(float, source_tokens[1:4])),
                )
                self.assertEqual(exported_tokens[4:], source_tokens[4:])

    def test_rejects_reversed_range(self):
        with self.assertRaisesRegex(ValueError, "x 方向最小值"):
            export_elements_by_range(
                "not_used.dat",
                "not_used_output.dat",
                (1, 0, 0, 1, 0, 1),
            )


if __name__ == "__main__":
    unittest.main()
