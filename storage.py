"""Load and save task data as JSON, beside the application files."""

import csv
import json
import locale
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from tasks import validate_details


# Use this file's folder, regardless of where the terminal was opened.
DATA_FILE = Path(__file__).resolve().parent / "tasks.json"


def validate_tasks(tasks):
    """Reject damaged data before using it or replacing a saved file."""
    if not isinstance(tasks, list):
        raise ValueError("The saved data must be a list of tasks.")
    ids = set()
    for task in tasks:
        if not isinstance(task, dict):
            raise ValueError("Each saved task must be a dictionary.")
        task_id = task.get("id")
        if type(task_id) is not int or task_id < 1 or task_id in ids:
            raise ValueError("Each task needs a unique positive numeric ID.")
        if not isinstance(task.get("title"), str) or not task["title"].strip():
            raise ValueError("Each task needs a non-empty title.")
        if type(task.get("completed")) is not bool:
            raise ValueError("Each task needs a True/False completion status.")
        # Step 2 files have no extra fields: accept sensible defaults.
        validate_details(
            task.get("priority", "Medium"), task.get("due_date", ""),
            task.get("category", "Uncategorized"),
        )
        ids.add(task_id)


def load_tasks(path=DATA_FILE):
    """A missing file means a first launch; damaged files raise an error."""
    path = Path(path)
    try:
        with path.open("r", encoding="utf-8") as file:
            tasks = json.load(file)
    except FileNotFoundError:
        return []
    validate_tasks(tasks)
    # Upgrade in memory only. Loading alone does not rewrite the saved file.
    return [dict(task, priority=task.get("priority", "Medium"),
                 due_date=task.get("due_date", ""),
                 category=task.get("category", "Uncategorized")) for task in tasks]


def save_tasks(tasks, path=DATA_FILE):
    """Write a temporary file, then replace the old file when ready."""
    validate_tasks(tasks)
    path = Path(path)
    temporary_path = None
    try:
        # Close the temporary file before replacing: required on Windows.
        with NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent,
            prefix=".studytasks-", suffix=".tmp", delete=False,
        ) as file:
            temporary_path = Path(file.name)
            json.dump(tasks, file, ensure_ascii=False, indent=2)
            file.write("\n")
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def csv_separator():
    """Respect Windows/Excel regional separators without changing settings."""
    if os.name == "nt":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\International") as key:
                value, _ = winreg.QueryValueEx(key, "sList")
                if value in (",", ";", "\t"):
                    return value
        except OSError:
            pass
    return ";" if locale.localeconv().get("decimal_point") == "," else ","


def export_csv(tasks, path, delimiter=None):
    """Export a spreadsheet-friendly copy without changing the task data."""
    validate_tasks(tasks)
    path = Path(path)
    if path.suffix.lower() != ".csv" or path.resolve() == DATA_FILE.resolve():
        raise ValueError("Choose a .csv file for the export.")
    temporary_path = None
    try:
        with NamedTemporaryFile(
            mode="w", encoding="utf-8-sig", newline="", dir=path.parent,
            prefix=".studytasks-export-", suffix=".tmp", delete=False,
        ) as file:
            temporary_path = Path(file.name)
            writer = csv.writer(file, delimiter=delimiter or csv_separator())
            writer.writerow(["ID", "Task", "Status", "Priority", "Deadline", "Category"])
            for task in tasks:
                writer.writerow([
                    task["id"], task["title"], "Completed" if task["completed"] else "Pending",
                    task.get("priority", "Medium"), task.get("due_date", ""),
                    task.get("category", "Uncategorized"),
                ])
        temporary_path.replace(path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
