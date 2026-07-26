from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from aprepost2.services.search import search_nearest_elements, search_nearest_nodes
from aprepost2.ui.task_catalog import TASKS
from tests.test_core import MESH_TEXT


class SearchServiceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.mesh = self.root / "mesh.dat"
        self.mesh.write_text(MESH_TEXT, encoding="utf-8")

    def tearDown(self):
        self.temporary.cleanup()

    def test_nearest_node_search(self):
        control = self.root / "nodes.txt"
        control.write_text("1\nP1 100 0.9 0.0 0.0\n", encoding="utf-8")
        output = self.root / "nodes.xlsx"
        search_nearest_nodes(str(self.mesh), str(control), str(output))
        frame = pd.read_excel(output)
        self.assertEqual(int(frame.loc[0, "节点id"]), 2)

    def test_nearest_element_respects_material_filter(self):
        control = self.root / "elements.txt"
        control.write_text("1\nP1 100 0.1 0.1 0.1 2\n", encoding="utf-8")
        output = self.root / "elements.xlsx"
        search_nearest_elements(str(self.mesh), str(control), str(output))
        frame = pd.read_excel(output)
        self.assertEqual(int(frame.loc[0, "单元id"]), 2)
        self.assertEqual(int(frame.loc[0, "单元材料号"]), 2)

    def test_catalog_covers_original_main_window_actions(self):
        self.assertEqual(len(TASKS), 26)
        self.assertEqual({task.category for task in TASKS}, {"前处理", "后处理"})


if __name__ == "__main__":
    unittest.main()
