"""Run with: python -m streamlit run app.py"""

import calendar
import csv
import hashlib
import html
import io
import json
from datetime import date

import pandas as pd
import streamlit as st

from storage import DATA_FILE, csv_separator, load_tasks, save_tasks
from tasks import PRIORITIES, SORT_OPTIONS, add_task, delete_task, filter_tasks, sort_tasks, toggle_task, update_task


DEFAULT_CATEGORIES = {"Personal", "Health", "Work", "Uncategorized", "Studies"}
PRIORITY_COLORS = {"High": ("#FFE8ED", "#AF3655"), "Medium": ("#FFF0D6", "#92610E"), "Low": ("#DFF5E9", "#237957")}
CATEGORY_COLORS = {
    "personal": ("#F0E6FF", "#8151AF"), "health": ("#DFF5E9", "#237957"),
    "work": ("#E4EDFF", "#3D64B0"), "uncategorized": ("#ECEFF4", "#657087"),
    "studies": ("#FFF0D9", "#93631C"),
}


def category_colors(name):
    return CATEGORY_COLORS.get(name.strip().casefold(), ("#DEF2F5", "#337986"))


def csv_bytes(tasks, separator):
    """Build a downloadable copy; comma/semicolon quoting preserves text."""
    output = io.StringIO(newline="")
    writer = csv.writer(output, delimiter=separator)
    writer.writerow(["ID", "Task", "Status", "Priority", "Deadline", "Category"])
    for task in tasks:
        writer.writerow([task["id"], task["title"], "Completed" if task["completed"] else "Pending",
                         task["priority"], task["due_date"], task["category"]])
    return output.getvalue().encode("utf-8-sig")


def badge(text, colors):
    background, foreground = colors
    return f'<span class="badge" style="background:{background};color:{foreground}">{html.escape(text)}</span>'


def deadline_caption(task):
    if not task["due_date"]:
        return "No deadline"
    if task["completed"]:
        return "Completed"
    days = (date.fromisoformat(task["due_date"]) - date.today()).days
    if days == 0:
        return "Due today"
    if days == 1:
        return "Due tomorrow"
    return f"{abs(days)} days overdue" if days < 0 else f"Due in {days} days"


def close_dialog():
    st.session_state.pop("dialog", None)


@st.dialog("Task details", width="large", on_dismiss=close_dialog)
def task_editor(task_id=None):
    # Read again on dialog reruns, so edits do not reuse an old disk snapshot.
    try:
        tasks = load_tasks()
    except (OSError, ValueError) as error:
        st.error(f"Cannot read saved tasks: {error}")
        return
    task = next((item for item in tasks if item["id"] == task_id), None)
    if task_id is not None and task is None:
        st.error("This task no longer exists. Close this dialog and refresh the page.")
        return
    prefix = f"editor_{st.session_state.get('editor_nonce', 0)}_{task_id}"
    st.caption("EDIT TASK" if task else "CREATE SOMETHING WORTH FINISHING")
    title = st.text_input("Task title", value=task["title"] if task else "", key=prefix + "title")
    left, right = st.columns(2)
    categories = sorted(DEFAULT_CATEGORIES | {item["category"] for item in tasks})
    with left:
        priority = st.selectbox("Priority", PRIORITIES, index=PRIORITIES.index(task["priority"]) if task else 1, key=prefix + "priority")
    with right:
        category_options = categories + ["+ Create a category"]
        category = st.selectbox("Category", category_options, index=categories.index(task["category"] if task else "Personal"), key=prefix + "category")
    if category == "+ Create a category":
        category = st.text_input("New category name", key=prefix + "custom_category")
    enabled = st.checkbox("Set a deadline", value=bool(task and task["due_date"]), key=prefix + "has_deadline")
    deadline = ""
    if enabled:
        initial = date.fromisoformat(task["due_date"]) if task and task["due_date"] else date.today()
        st.caption("Choose a year, month, and day. Only valid dates can be selected.")
        years = sorted(set(range(date.today().year - 20, date.today().year + 31)) | {initial.year})
        year_col, month_col, day_col = st.columns(3)
        with year_col:
            year = st.selectbox("Year", years, index=years.index(initial.year), key=prefix + "year")
        with month_col:
            month = st.selectbox("Month", list(range(1, 13)), index=initial.month - 1, format_func=lambda number: calendar.month_name[number], key=prefix + "month")
        with day_col:
            last_day = calendar.monthrange(year, month)[1]
            day = st.selectbox("Day", list(range(1, last_day + 1)), index=min(initial.day, last_day) - 1, key=prefix + f"day_{year}_{month}")
        deadline = date(year, month, day).isoformat()
    st.markdown("---")
    cancel, submit = st.columns([1, 2])
    if cancel.button("Cancel", key=prefix + "cancel", width="stretch"):
        close_dialog()
        st.rerun()
    if submit.button("Save changes" if task else "Create task", type="primary", key=prefix + "submit", width="stretch"):
        try:
            # Load at the moment of saving, retaining unrelated saved changes.
            updated = load_tasks()
            values = (title, priority, deadline, category)
            result = update_task(updated, task_id, *values) if task else add_task(updated, *values)
            save_tasks(updated)
        except (OSError, ValueError) as error:
            st.error(f"The change was not saved: {error}")
            return
        st.session_state.selected_id = result["id"]
        st.session_state.flash = "Task saved."
        close_dialog()
        st.rerun()


@st.dialog("Delete this task?", on_dismiss=close_dialog)
def confirm_delete(task_id):
    st.write("This removes the task from your saved list.")
    cancel, confirm = st.columns(2)
    if cancel.button("Cancel", width="stretch"):
        close_dialog()
        st.rerun()
    if confirm.button("Delete task", type="primary", width="stretch"):
        try:
            updated = load_tasks()
            delete_task(updated, task_id)
            save_tasks(updated)
        except (OSError, ValueError) as error:
            st.error(f"Deletion was not saved: {error}")
            return
        st.session_state.selected_id = None
        st.session_state.flash = "Task deleted."
        close_dialog()
        st.rerun()


def reset_filters():
    st.session_state.view = "All tasks"
    st.session_state.query = ""
    st.session_state.category = "All categories"
    st.session_state.selected_id = None


def main():
    st.set_page_config(page_title="StudyTasks", page_icon="✅", layout="wide", initial_sidebar_state="expanded")
    st.markdown('''<style>
    .stApp {background:#F6F7FB;}
    .block-container {padding-top:2rem; padding-bottom:1.5rem; max-width:1600px;}
    h1,h2,h3 {letter-spacing:-.035em;}
    h1 {font-size:2.2rem !important; font-weight:750 !important;}
    [data-testid="stSidebar"] {background:#202437;}
    [data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] p,[data-testid="stSidebar"] label,
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {color:#D3D6E5;}
    [data-testid="stSidebar"] [role="radiogroup"] label {padding:.45rem .3rem;}
    [data-testid="stVerticalBlockBorderWrapper"] {background:white; border-radius:18px;}
    .eyebrow {color:#8C87AC;font-size:.72rem;font-weight:700;letter-spacing:.12em;margin-bottom:8px;}
    .stat-card {background:white;border:1px solid #E8EAF2;border-radius:16px;padding:18px 21px;animation:arrive .3s ease-out;}
    .stat-name {font-size:.73rem;letter-spacing:.07em;color:#868B9D;font-weight:650;}
    .stat-value {font-size:2rem;font-weight:750;line-height:1.4;letter-spacing:-.05em;}
    .stat-percent {color:#8B8FA0;font-size:.78rem;}
    .badge {display:inline-block;padding:6px 11px;border-radius:8px;font-size:.75rem;font-weight:650;margin:0 5px 8px 0;}
    .task-title {font-size:1.45rem;font-weight:720;line-height:1.35;overflow-wrap:anywhere;color:#282B40;margin:12px 0 18px;}
    .muted {color:#9295A8;font-size:.85rem;}
    .brand {color:white;font-size:1.4rem;font-weight:750;letter-spacing:-.04em;margin:12px 0 24px;}
    div.stButton>button,div.stDownloadButton>button {border-radius:10px;min-height:42px;transition:transform .15s ease,box-shadow .15s ease;}
    div.stButton>button:hover,div.stDownloadButton>button:hover {transform:translateY(-1px);box-shadow:0 5px 16px #7367f014;}
    [data-testid="stProgressBar"]>div>div>div {transition:width .4s ease;}
    @keyframes arrive {from {opacity:.4;transform:translateY(5px)} to {opacity:1;transform:translateY(0)}}
    @media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;}}
    </style>''', unsafe_allow_html=True)
    try:
        tasks = load_tasks()
    except (OSError, ValueError) as error:
        st.error(f"Cannot load {DATA_FILE.name}: {error}. The saved file has not been changed.")
        st.stop()
    if "flash" in st.session_state:
        st.toast(st.session_state.pop("flash"), icon="✅")
    categories = sorted(DEFAULT_CATEGORIES | {task["category"] for task in tasks})
    today = date.today().isoformat()
    total = len(tasks)
    completed = sum(task["completed"] for task in tasks)
    overdue = sum(bool(not task["completed"] and task["due_date"] and task["due_date"] < today) for task in tasks)
    counts = {"All tasks": total, "Pending": total - completed, "Completed": completed, "Overdue": overdue}
    with st.sidebar:
        st.markdown('<div class="brand">S / StudyTasks</div><div class="eyebrow">MY WORKSPACE</div>', unsafe_allow_html=True)
        view = st.radio("Navigation", list(counts), key="view", label_visibility="collapsed", format_func=lambda name: f"{name}  ·  {counts[name]}")
        st.divider()
        st.caption("YOUR PROGRESS")
        st.progress(completed / total if total else 0, text=f"{completed / total * 100:.0f}% complete" if total else "0% complete")
        st.caption("Changes save automatically on this computer.")
        st.divider()
        separator_choice = st.selectbox("CSV separator", ["Excel (regional)", "Comma", "Semicolon"], help="Use Semicolon if Excel opens everything in one column.")
    separator = csv_separator() if separator_choice == "Excel (regional)" else "," if separator_choice == "Comma" else ";"

    heading, export_col, add_col = st.columns([6, 1.7, 1.5], vertical_alignment="center")
    with heading:
        st.markdown('<div class="eyebrow">PERSONAL PLANNER</div>', unsafe_allow_html=True)
        st.title("Your workspace" if view == "All tasks" else view)
        st.caption("A clear view of what matters next.")
    with export_col:
        st.download_button("Export CSV", data=csv_bytes(sort_tasks(tasks, st.session_state.get("sort", "Priority")), separator), file_name="StudyTasks_export.csv", mime="text/csv", disabled=not tasks, width="stretch", help="Exports all tasks, including tasks hidden by filters.")
    with add_col:
        if st.button("＋ New task", type="primary", width="stretch"):
            st.session_state.editor_nonce = st.session_state.get("editor_nonce", 0) + 1
            st.session_state.dialog = ("edit", None)
    st.write("")
    stat_colors = ["#7367F0", "#B98427", "#2C9270", "#C04F72"]
    for column, (name, count), color in zip(st.columns(4), counts.items(), stat_colors):
        percentage = f"{count / total * 100:.0f}% of all tasks" if total else "0% of all tasks"
        column.markdown(f'<div class="stat-card"><div class="stat-name">{name.upper()}</div><div class="stat-value" style="color:{color}">{count}</div><div class="stat-percent">{percentage}</div></div>', unsafe_allow_html=True)
    st.write("")
    collection, detail = st.columns([3.2, 1.25], gap="large")
    with collection, st.container(border=True):
        st.subheader("Task collection")
        search, category_col, sort_col, reset = st.columns([2.5, 1.6, 1.5, .9], vertical_alignment="bottom")
        query = search.text_input("Search tasks", key="query", placeholder="Title or category…")
        category = category_col.selectbox("Category", ["All categories"] + categories, key="category")
        order = sort_col.selectbox("Sort by", SORT_OPTIONS, key="sort", index=1)
        reset.button("Reset", on_click=reset_filters, width="stretch")
        visible = filter_tasks(tasks, query, "Pending" if view == "Overdue" else view, None if category == "All categories" else category)
        if view == "Overdue":
            visible = [task for task in visible if task["due_date"] and task["due_date"] < today]
        visible = sort_tasks(visible, order)
        st.caption(f"{len(visible)} of {total} tasks shown · Select a row to view its details")
        if visible:
            rows = [{"Task": task["title"], "Status": "Completed" if task["completed"] else "Pending", "Priority": task["priority"],
                     "Deadline": date.fromisoformat(task["due_date"]) if task["due_date"] else None, "Category": task["category"]} for task in visible]
            frame = pd.DataFrame(rows)
            styled = frame.style.map(lambda value: f"background-color:{PRIORITY_COLORS[value][0]};color:{PRIORITY_COLORS[value][1]};font-weight:600", subset=["Priority"])
            styled = styled.map(lambda value: f"background-color:{category_colors(value)[0]};color:{category_colors(value)[1]}", subset=["Category"])
            # A content-dependent key prevents a stale row position selecting a
            # different task after sorting, filtering, editing, or deletion.
            signature = hashlib.sha256(json.dumps(visible, sort_keys=True).encode()).hexdigest()[:16]
            event = st.dataframe(styled, key="table_" + signature, hide_index=True, width="stretch", height=480,
                on_select="rerun", selection_mode="single-row", column_config={"Task": st.column_config.TextColumn(width="large"), "Deadline": st.column_config.DateColumn(format="DD/MM/YYYY")})
            if event.selection.rows:
                st.session_state.selected_id = visible[event.selection.rows[0]]["id"]
        else:
            st.info("No tasks match this view. Use Reset to show all tasks." if tasks else "Your next task starts here. Click ＋ New task to get started.")

    selected = next((task for task in visible if task["id"] == st.session_state.get("selected_id")), None)
    with detail, st.container(border=True):
        st.markdown('<div class="eyebrow">TASK DETAILS</div>', unsafe_allow_html=True)
        if selected is None:
            st.markdown('<div class="task-title">A little focus,<br>a clearer day.</div><p class="muted">Select a task from the collection to see its priority, category, and deadline.</p>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="task-title">{html.escape(selected["title"])}</div>', unsafe_allow_html=True)
            st.caption("Completed" if selected["completed"] else "In progress")
            urgent = selected["due_date"] and selected["due_date"] <= today and not selected["completed"]
            st.markdown(badge(selected["priority"].upper() + " PRIORITY", PRIORITY_COLORS[selected["priority"]]) + badge(selected["category"], category_colors(selected["category"])) + badge(deadline_caption(selected), ("#FFE8ED", "#AF3655") if urgent else ("#EEEAFF", "#6D59B4")), unsafe_allow_html=True)
            st.caption(date.fromisoformat(selected["due_date"]).strftime("%d/%m/%Y") if selected["due_date"] else "No deadline set")
            st.divider()
            if st.button("Mark pending" if selected["completed"] else "Mark complete", type="primary", width="stretch"):
                try:
                    updated = load_tasks()
                    toggle_task(updated, selected["id"])
                    save_tasks(updated)
                except (OSError, ValueError) as error:
                    st.error(f"The change was not saved: {error}")
                else:
                    st.session_state.flash = "Task status saved."
                    st.rerun()
            edit, delete = st.columns(2)
            if edit.button("Edit", width="stretch"):
                st.session_state.editor_nonce = st.session_state.get("editor_nonce", 0) + 1
                st.session_state.dialog = ("edit", selected["id"])
            if delete.button("Delete", width="stretch"):
                st.session_state.dialog = ("delete", selected["id"])
    st.caption("Saved locally · All changes persist after closing and reopening")
    dialog = st.session_state.get("dialog")
    if dialog:
        task_editor(dialog[1]) if dialog[0] == "edit" else confirm_delete(dialog[1])


if __name__ == "__main__":
    main()
