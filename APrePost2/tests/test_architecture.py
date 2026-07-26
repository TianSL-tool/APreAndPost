from __future__ import annotations

import ast
import unittest
from pathlib import Path

from aprepost2.ui.task_catalog import TASKS, control_file_help_for


class ArchitectureTests(unittest.TestCase):
    def test_runtime_has_no_old_project_imports(self):
        package_root = Path(__file__).resolve().parents[1] / "aprepost2"
        forbidden = {"pre_group", "post", "Node", "Element", "Face"}
        violations: list[str] = []
        for source in package_root.rglob("*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    roots = {alias.name.split(".", 1)[0] for alias in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    roots = {node.module.split(".", 1)[0]}
                else:
                    continue
                matched = roots & forbidden
                if matched:
                    violations.append(f"{source.name}: {sorted(matched)}")
            self.assertNotIn("sys.path", source.read_text(encoding="utf-8"))
        self.assertEqual(violations, [])

    def test_all_task_handlers_are_new_project_services(self):
        self.assertEqual(len(TASKS), 26)
        for task in TASKS:
            self.assertTrue(
                task.handler.__module__.startswith("aprepost2."),
                f"{task.key} 仍指向外部实现：{task.handler.__module__}",
            )

    def test_control_file_tasks_have_log_help(self):
        missing: list[str] = []
        for task in TASKS:
            needs_help = any(
                "control" in field.name
                or "控制" in field.label
                or field.name == "element_ids_path"
                or "单元号文件" in field.label
                for field in task.fields
            )
            if needs_help and not control_file_help_for(task):
                missing.append(task.key)
        self.assertEqual(missing, [])

    def test_project_no_longer_declares_pyvista(self):
        project = (
            Path(__file__).resolve().parents[1] / "pyproject.toml"
        ).read_text(encoding="utf-8")
        self.assertNotIn("pyvista", project.lower())


if __name__ == "__main__":
    unittest.main()
