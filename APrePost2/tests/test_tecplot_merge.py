from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from aprepost2.services.tecplot_merge import (
    discover_plt_files,
    infer_tecplot_step,
    merge_tecplot_single_step,
    group_tecplot_step_files,
    merge_tecplot_step_series,
    parse_tecplot_ascii,
)


def _plt_text(variable_y: str, first_value: int, second_value: int) -> str:
    return (
        'TITLE = "result"\n'
        f'VARIABLES = "X", "{variable_y}"\n'
        'ZONE T="old-1", I=1, F=POINT\n'
        f'0 {first_value}\n'
        'ZONE T="old-2", I=1, F=POINT\n'
        f'0 {second_value}\n'
    )


def _binary_string(value: str) -> bytes:
    return b"".join(struct.pack("<i", ord(char)) for char in value) + struct.pack("<i", 0)


def _binary_step(path: Path, value: bytes) -> None:
    zone_marker = struct.pack("<f", 299.0)
    end_header = struct.pack("<f", 357.0)
    content = (
        b"#!TDV112"
        + struct.pack("<ii", 1, 0)
        + _binary_string("result")
        + struct.pack("<i", 1)
        + _binary_string("X")
        + zone_marker
        + struct.pack("<i", len(value))
        + end_header
        + zone_marker
        + value
    )
    path.write_bytes(content)


class TecplotMergeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def test_extracts_requested_zone_in_user_order_and_renames_cases(self):
        first = self.root / "first.plt"
        second_dir = self.root / "other"
        second_dir.mkdir()
        second = second_dir / "second.plt"
        first.write_text(_plt_text("Y", 11, 12), encoding="utf-8")
        second.write_text(_plt_text("Y", 21, 22), encoding="utf-8")
        original_first = first.read_bytes()
        original_second = second.read_bytes()
        output = self.root / "merged.plt"

        result = merge_tecplot_single_step(
            [str(second), str(first)],
            ["下游工况", "上游工况"],
            2,
            str(output),
        )

        merged = output.read_text(encoding="utf-8")
        self.assertEqual(merged.count("VARIABLES"), 1)
        self.assertEqual(merged.count("ZONE"), 2)
        self.assertLess(merged.index('T="下游工况"'), merged.index('T="上游工况"'))
        self.assertIn("0 22", merged)
        self.assertIn("0 12", merged)
        self.assertNotIn("0 21", merged)
        self.assertNotIn("0 11", merged)
        self.assertEqual(first.read_bytes(), original_first)
        self.assertEqual(second.read_bytes(), original_second)
        self.assertEqual(result.metrics["file_count"], 2)

    def test_rejects_missing_step_without_creating_output(self):
        source = self.root / "one.plt"
        source.write_text(_plt_text("Y", 1, 2), encoding="utf-8")
        output = self.root / "missing.plt"
        with self.assertRaisesRegex(ValueError, "指定计算步 3 不存在"):
            merge_tecplot_single_step([str(source)], ["工况"], 3, str(output))
        self.assertFalse(output.exists())

    def test_same_source_can_appear_multiple_times_in_requested_order(self):
        baseline = self.root / "baseline.plt"
        other = self.root / "other.plt"
        baseline.write_text(_plt_text("Y", 11, 12), encoding="utf-8")
        other.write_text(_plt_text("Y", 21, 22), encoding="utf-8")
        output = self.root / "repeated-baseline.plt"

        merge_tecplot_single_step(
            [str(baseline), str(other), str(baseline)],
            ["基准-前", "对比", "基准-后"],
            1,
            str(output),
        )

        merged = output.read_text(encoding="utf-8")
        self.assertEqual(merged.count("ZONE"), 3)
        self.assertLess(merged.index('T="基准-前"'), merged.index('T="对比"'))
        self.assertLess(merged.index('T="对比"'), merged.index('T="基准-后"'))
        self.assertEqual(merged.count("0 11"), 2)

    def test_rejects_incompatible_variables_without_creating_output(self):
        first = self.root / "first.plt"
        second = self.root / "second.plt"
        first.write_text(_plt_text("Y", 1, 2), encoding="utf-8")
        second.write_text(_plt_text("Z", 3, 4), encoding="utf-8")
        output = self.root / "bad.plt"
        with self.assertRaisesRegex(ValueError, "变量体系不兼容"):
            merge_tecplot_single_step(
                [str(first), str(second)], ["A", "B"], 1, str(output)
            )
        self.assertFalse(output.exists())

    def test_rejects_zone_that_shares_data_with_another_zone(self):
        source = self.root / "shared.plt"
        source.write_text(
            'VARIABLES = "X"\n'
            'ZONE T="one", I=1, F=POINT\n1\n'
            'ZONE T="two", I=1, VARSHARELIST=([1]=1)\n',
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "跨 Zone 共享数据"):
            merge_tecplot_single_step(
                [str(source)], ["A"], 2, str(self.root / "shared-out.plt")
            )

    def test_discovers_folders_with_and_without_recursion(self):
        direct = self.root / "a.plt"
        ignored = self.root / "b.txt"
        nested_dir = self.root / "nested"
        nested_dir.mkdir()
        nested = nested_dir / "c.PLT"
        direct.write_text("", encoding="ascii")
        ignored.write_text("", encoding="ascii")
        nested.write_text("", encoding="ascii")
        self.assertEqual(discover_plt_files((self.root,), recursive=False), (direct,))
        self.assertEqual(
            discover_plt_files((self.root,), recursive=True), (direct, nested)
        )

    def test_parser_accepts_multiline_variable_declaration(self):
        source = self.root / "multiline.plt"
        source.write_text(
            'TITLE="x"\nVARIABLES = "X"\n "Stress XX"\nZONE I=1\n0 1\n',
            encoding="utf-8",
        )
        parsed = parse_tecplot_ascii(source)
        self.assertEqual(parsed.variables, ("X", "Stress XX"))
        self.assertEqual(len(parsed.zones), 1)


    def test_groups_step_files_by_trailing_numeric_step(self):
        paths = [
            self.root / "stress_10.plt",
            self.root / "stress_2.plt",
            self.root / "stress_1.plt",
            self.root / "single_4.plt",
        ]
        for path in paths:
            path.write_bytes(b"x")

        groups = group_tecplot_step_files(paths)

        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].name, "stress")
        self.assertEqual(groups[0].steps, (1, 2, 10))
        self.assertEqual(
            tuple(path.name for path in groups[0].paths),
            ("stress_1.plt", "stress_2.plt", "stress_10.plt"),
        )

    def test_file_without_trailing_number_is_not_counted(self):
        self.assertIsNone(infer_tecplot_step(self.root / "stress.plt"))
        self.assertEqual(
            infer_tecplot_step(self.root / "stress12.plt"), ("stress", 12)
        )

    def test_merges_ascii_step_files_in_numeric_order(self):
        later = self.root / "stress_10.plt"
        earlier = self.root / "stress_2.plt"
        later.write_text(
            'VARIABLES = "X"\nZONE T="ten", I=1, F=POINT\n10\n',
            encoding="utf-8",
        )
        earlier.write_text(
            'VARIABLES = "X"\nZONE T="two", I=1, F=POINT\n2\n',
            encoding="utf-8",
        )
        output_directory = self.root / "merged"

        result = merge_tecplot_step_series(
            str(self.root), str(output_directory)
        )

        output = output_directory / "stress_merged.plt"
        text = output.read_text(encoding="utf-8")
        self.assertLess(text.index('T="two"'), text.index('T="ten"'))
        self.assertEqual(result.metrics["file_count"], 2)

    def test_merges_single_zone_binary_step_files_without_changing_sources(self):
        later = self.root / "stress_10.plt"
        earlier = self.root / "stress_2.plt"
        _binary_step(later, b"ten")
        _binary_step(earlier, b"two")
        originals = (earlier.read_bytes(), later.read_bytes())
        output_directory = self.root / "merged"

        merge_tecplot_step_series(str(self.root), str(output_directory))

        output = (output_directory / "stress_merged.plt").read_bytes()
        end_header = struct.pack("<f", 357.0)
        zone_marker = struct.pack("<f", 299.0)
        header_end = output.index(end_header)
        self.assertEqual(output[:header_end].count(zone_marker), 2)
        self.assertTrue(
            output[header_end + 4 :].endswith(
                zone_marker + b"two" + zone_marker + b"ten"
            )
        )
        self.assertEqual((earlier.read_bytes(), later.read_bytes()), originals)

    def test_mixed_format_error_lists_concrete_files(self):
        ascii_file = self.root / "stress_1.plt"
        binary_file = self.root / "stress_2.plt"
        ascii_file.write_text('VARIABLES = "X"\nZONE I=1\n1\n', encoding="utf-8")
        _binary_step(binary_file, b"two")

        with self.assertRaises(ValueError) as context:
            merge_tecplot_step_series(str(self.root), str(self.root / "merged"))

        message = str(context.exception)
        self.assertIn(str(ascii_file), message)
        self.assertIn(str(binary_file), message)
        self.assertIn("ASCII 文件（1 个）", message)
        self.assertIn("binary 文件（1 个）", message)

    def test_mixed_format_minor_files_are_excluded_without_deletion(self):
        ascii_file = self.root / "stress_1.plt"
        binary_files = [
            self.root / "stress_2.plt",
            self.root / "stress_3.plt",
        ]
        ascii_file.write_text('VARIABLES = "X"\nZONE I=1\n1\n', encoding="utf-8")
        _binary_step(binary_files[0], b"two")
        _binary_step(binary_files[1], b"three")
        original_ascii = ascii_file.read_bytes()

        result = merge_tecplot_step_series(
            str(self.root), str(self.root / "merged")
        )

        self.assertEqual(result.metrics["file_count"], 2)
        self.assertEqual(result.metrics["excluded_format_file_count"], 1)
        self.assertTrue((self.root / "merged" / "stress_merged.plt").is_file())
        self.assertEqual(ascii_file.read_bytes(), original_ascii)
        self.assertTrue(any(str(ascii_file) in line for line in result.log_lines))


if __name__ == "__main__":
    unittest.main()
