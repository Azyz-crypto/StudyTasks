"""Task data, validation, and sorting, independent of the interface."""

from datetime import date


PRIORITIES = ("High", "Medium", "Low")
SORT_OPTIONS = ("Added order", "Priority", "Deadline")


def validate_details(priority, due_date, category):
    """Check the extra fields, including dates read from a saved file."""
    if priority not in PRIORITIES:
        raise ValueError("Priority must be High, Medium, or Low.")
    if not isinstance(category, str) or not category.strip():
        raise ValueError("Please enter or choose a category.")
    if not isinstance(due_date, str):
        raise ValueError("The saved deadline must be text.")
    if due_date:
        try:
            if date.fromisoformat(due_date).isoformat() != due_date:
                raise ValueError
        except ValueError:
            raise ValueError("The saved deadline must be a valid YYYY-MM-DD date.") from None


def add_task(tasks, title, priority="Medium", due_date="", category="Uncategorized"):
    """Add a pending task with its priority, optional deadline, and category."""
    title = title.strip()
    category = category.strip()
    if not title:
        raise ValueError("Please enter a task title.")
    validate_details(priority, due_date, category)
    next_id = max((task["id"] for task in tasks), default=0) + 1
    task = {
        "id": next_id, "title": title, "completed": False,
        "priority": priority, "due_date": due_date, "category": category,
    }
    tasks.append(task)
    return task


def toggle_task(tasks, task_id):
    """Switch the task with this ID between pending and completed."""
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = not task["completed"]
            return task
    raise ValueError("This task could not be found.")


def update_task(tasks, task_id, title, priority, due_date, category):
    """Edit details while preserving a task's ID and completion state."""
    title = title.strip()
    category = category.strip()
    if not title:
        raise ValueError("Please enter a task title.")
    validate_details(priority, due_date, category)
    for task in tasks:
        if task["id"] == task_id:
            task.update(title=title, priority=priority, due_date=due_date, category=category)
            return task
    raise ValueError("This task could not be found.")


def filter_tasks(tasks, query="", status="All tasks", category=None):
    """Filter by title/category text, completion status, and category."""
    query = query.strip().casefold()
    return [task for task in tasks
            if (not query or query in task["title"].casefold() or query in task["category"].casefold())
            and (status == "All tasks" or (status == "Completed" and task["completed"])
                 or (status == "Pending" and not task["completed"]))
            and (category is None or task["category"] == category)]


def delete_task(tasks, task_id):
    """Delete the task with this ID, regardless of its displayed position."""
    for index, task in enumerate(tasks):
        if task["id"] == task_id:
            return tasks.pop(index)
    raise ValueError("This task could not be found.")


def sort_tasks(tasks, order):
    """Return a sorted display list without changing the stored list."""
    def priority_key(task):
        return PRIORITIES.index(task["priority"])

    def deadline_key(task):
        # ISO dates sort chronologically. No deadline goes after every date.
        return task["due_date"] or "9999-99-99"

    if order == "Priority":
        return sorted(tasks, key=lambda task: (priority_key(task), deadline_key(task), task["id"]))
    if order == "Deadline":
        return sorted(tasks, key=lambda task: (deadline_key(task), priority_key(task), task["id"]))
    if order == "Added order":
        return sorted(tasks, key=lambda task: task["id"])
    raise ValueError("Unknown sorting option.")
