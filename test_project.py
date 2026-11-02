"""Run with python -m unittest -v. All disk checks use temporary folders."""

import csv
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from storage import csv_separator, export_csv, load_tasks, save_tasks
from tasks import add_task, delete_task, filter_tasks, sort_tasks, toggle_task, update_task


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.path = self.folder / "tasks.json"

    def test_add_complete_undo_and_delete_duplicate_titles(self):
        tasks = []
        first = add_task(tasks, "Same title")
        second = add_task(tasks, "Same title")
        self.assertNotEqual(first["id"], second["id"])
        toggle_task(tasks, second["id"])
        self.assertFalse(first["completed"])
        self.assertTrue(second["completed"])
        toggle_task(tasks, second["id"])
        self.assertFalse(second["completed"])
        delete_task(tasks, first["id"])
        self.assertEqual(tasks, [second])

    def test_invalid_inputs_leave_data_unchanged(self):
        tasks = []
        for title, priority, deadline, category in (
            (" ", "High", "", "Studies"), ("A", "Urgent", "", "Studies"),
            ("A", "High", "2026-02-29", "Studies"), ("A", "High", "", " "),
        ):
            with self.assertRaises(ValueError):
                add_task(tasks, title, priority, deadline, category)
        self.assertEqual(tasks, [])

    def test_sorting_and_actions_use_ids(self):
        tasks = []
        low = add_task(tasks, "Earlier", "Low", "2026-11-01", "Studies")
        high = add_task(tasks, "Later", "High", "2026-11-10", "Work")
        medium = add_task(tasks, "No date", "Medium", "", "Personal")
        self.assertEqual(sort_tasks(tasks, "Priority"), [high, medium, low])
        self.assertEqual(sort_tasks(tasks, "Deadline"), [low, high, medium])
        visible = sort_tasks(tasks, "Priority")
        toggle_task(tasks, visible[0]["id"])
        self.assertTrue(high["completed"])
        self.assertFalse(low["completed"])
        self.assertEqual(tasks, [low, high, medium])

    def test_edit_preserves_id_and_completion(self):
        tasks = []
        task = add_task(tasks, "Old")
        toggle_task(tasks, task["id"])
        result = update_task(tasks, task["id"], "New", "High", "2028-02-29", "Research")
        self.assertEqual(result["id"], task["id"])
        self.assertTrue(result["completed"])
        self.assertEqual(result["title"], "New")
        self.assertEqual(result["category"], "Research")

    def test_search_and_filters(self):
        tasks = []
        pending = add_task(tasks, "Read Chapter", category="Studies")
        done = add_task(tasks, "Send email", category="Work")
        toggle_task(tasks, done["id"])
        self.assertEqual(filter_tasks(tasks, "CHAPTER", "Pending", "Studies"), [pending])
        self.assertEqual(filter_tasks(tasks, "work", "Completed"), [done])
        self.assertEqual(filter_tasks(tasks, "chapter", "Completed"), [])
        self.assertEqual(filter_tasks(tasks), tasks)

    def test_persistence_retains_all_fields_and_empty_list(self):
        tasks = []
        task = add_task(tasks, "Réviser Python", "High", "2028-02-29", "Études")
        toggle_task(tasks, task["id"])
        save_tasks(tasks, self.path)
        self.assertEqual(load_tasks(self.path), tasks)
        save_tasks([], self.path)
        self.assertEqual(load_tasks(self.path), [])

    def test_missing_and_legacy_files(self):
        self.assertEqual(load_tasks(self.path), [])
        original = [{"id": 7, "title": "Old task", "completed": True}]
        self.path.write_text(json.dumps(original), encoding="utf-8")
        before = self.path.read_bytes()
        loaded = load_tasks(self.path)
        self.assertEqual(loaded[0], dict(original[0], priority="Medium", due_date="", category="Uncategorized"))
        self.assertEqual(self.path.read_bytes(), before)

    def test_corrupt_data_is_not_overwritten(self):
        for content in ("{broken", "{}", '[{"id":1,"title":"x","completed":"false"}]'):
            self.path.write_text(content, encoding="utf-8")
            with self.assertRaises(ValueError):
                load_tasks(self.path)
            self.assertEqual(self.path.read_text(encoding="utf-8"), content)

    def test_failed_save_keeps_previous_file(self):
        save_tasks([], self.path)
        before = self.path.read_bytes()
        with patch("storage.Path.replace", side_effect=PermissionError("Blocked")):
            with self.assertRaises(PermissionError):
                save_tasks([{"id": 1, "title": "New", "completed": False}], self.path)
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual(list(self.folder.glob("*.tmp")), [])

    def test_csv_quotes_unicode_and_all_fields(self):
        tasks = []
        task = add_task(tasks, 'Réviser, "Python"\nand files', "High", "2026-11-05", "Études")
        toggle_task(tasks, task["id"])
        add_task(tasks, "Second task", "Low", "", "Personal")
        save_tasks(tasks, self.path)
        before = self.path.read_bytes()
        target = self.folder / "export.csv"
        export_csv(tasks, target, delimiter=",")
        with target.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Task"], task["title"])
        self.assertEqual(rows[0]["Status"], "Completed")
        self.assertEqual(rows[0]["Category"], "Études")
        self.assertEqual(rows[0]["Deadline"], "2026-11-05")
        self.assertEqual(rows[1]["Deadline"], "")
        self.assertEqual(self.path.read_bytes(), before)

    def test_semicolon_export_and_windows_separator(self):
        tasks = []
        add_task(tasks, 'Task; with comma, and accents é')
        target = self.folder / "regional.csv"
        export_csv(tasks, target, delimiter=";")
        with target.open(encoding="utf-8-sig", newline="") as file:
            rows = list(csv.DictReader(file, delimiter=";"))
        self.assertEqual(rows[0]["Task"], tasks[0]["title"])
        self.assertEqual(len(rows[0]), 6)
        registry = SimpleNamespace(HKEY_CURRENT_USER=1, OpenKey=MagicMock(),
                                   QueryValueEx=MagicMock(return_value=(";", 1)))
        with patch("storage.os.name", "nt"), patch.dict("sys.modules", {"winreg": registry}):
            self.assertEqual(csv_separator(), ";")

    def test_csv_rejects_non_csv_path(self):
        save_tasks([], self.path)
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            export_csv([], self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_failed_export_preserves_existing_destination(self):
        target = self.folder / "export.csv"
        target.write_text("Previous export", encoding="utf-8")
        with patch("storage.Path.replace", side_effect=PermissionError("Blocked")):
            with self.assertRaises(PermissionError):
                export_csv([], target)
        self.assertEqual(target.read_text(encoding="utf-8"), "Previous export")
        self.assertEqual(list(self.folder.glob("*.tmp")), [])


if __name__ == "__main__":
    unittest.main()
