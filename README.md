# StudyTasks - Streamlit edition

A local browser app with a modern dashboard, task table, sidebar navigation,
live counts/percentages, priority/category colors, task details, create/edit
dialogs, date selectors, sorting, filters, and CSV downloads.

## Quick launch for the professor

Read `START_HERE.txt`. On Windows with Python 3.13 installed, extract the
complete ZIP and double-click `START.bat`. The launcher selects the correct
folder, creates a project environment, installs dependencies on first use, and
starts Streamlit. Keep its terminal window open while using the app.

## Install and run on Windows

Use Python 3.13 (64-bit). Python 3.15 can trigger a pandas source build with
these dependency versions.

1. Close the old app and extract the complete ZIP using **Extract All**.
2. Open `StudyTasks_Streamlit`, the folder containing `app.py`.
3. COPY your existing `tasks.json` into this folder to keep your tasks.
   Keep your original folder as a backup. No file conversion is needed.
4. In File Explorer, type `cmd` in the address bar and press Enter.
5. Install the dependencies (once):

   ```bash
   py -3.13 -m pip install -r requirements.txt
   ```

6. Start the application:

   ```bash
   py -3.13 -m streamlit run app.py
   ```

The browser normally opens automatically. Otherwise open the local URL shown
in the terminal, usually `http://localhost:8501`. Keep the terminal running
while using the app. Press Ctrl+C in the terminal to stop it.

If your Python command is `python`, use it instead of `py`. On macOS/Linux,
use `python3`. Run the command from this folder so the included Streamlit
configuration is loaded. There is no `main.py` in this edition.

## Use the app

- Click **+ New task** to create a task. Blank titles/categories are rejected.
- Select a row in the table to open its details on the right.
- Mark complete/pending, edit task details, or delete with confirmation.
- Use the sidebar for All tasks, Pending, Completed, or Overdue.
- Combine search, categories, and priority/deadline/added-order sorting.
- Reset clears the filters. Completion percentages use all saved tasks,
  regardless of filters, and update after changes.
- High priority is red, Medium amber, Low green. Personal is purple,
  Health green, Work blue, Uncategorized gray, and Studies orange.
- Choose an existing category or create a custom one in the task dialog.

## Dates

Enable **Set a deadline** in the task dialog. Choose year, month, and day
from the selectors. Only valid dates can be selected; February respects leap
years. Disable the option to remove a deadline. Dates are saved in ISO format
and displayed as DD/MM/YYYY. Dates from existing saved tasks are retained.

## CSV and Excel

The top **Export CSV** button downloads every task in the selected sort order,
including tasks hidden by filters. Priority/category colors are interface
styling and are not saved in CSV.

The sidebar lets you choose **Excel (regional)**, **Comma**, or **Semicolon**.
If Excel opens everything in one column, choose Semicolon and download again.
Regional mode reads the list separator on the computer running the Python app;
it does not read the settings of a remote browser. Accents and quoted text are
retained with UTF-8 encoding. For explicit importing, Excel's Data > From
Text/CSV allows you to select the correct separator.

## Saving

Accepted task changes save automatically to `tasks.json` beside `storage.py`.
The file remains compatible with the previous task structure. Step 2 files
receive default values for missing priority/category/deadline fields.

A missing file starts an empty list. Invalid or unreadable data displays an
error without replacing the file. A failed write leaves the saved data intact.
Use this local version with one active editing session. It is not a shared
multi-user database. JSON persistence is on the computer running Python.

## Files

- `app.py`: Streamlit interface and events.
- `tasks.py`: task validation, operations, filtering, and sorting.
- `storage.py`: JSON loading/saving and regional CSV utilities.
- `requirements.txt`: dependencies.
- `.streamlit/config.toml`: theme and local server settings.
- `test_project.py`: data/storage/export checks.

Run the included data checks with `py -m unittest -v`.
The interface has also been exercised using Streamlit's AppTest in isolated
temporary folders: add/edit/complete/delete, legacy loading, search/filters,
leap-year selectors, and input validation.

## Assignment requirement difference

This edition uses Streamlit and an interactive table instead of Tkinter and
a Listbox. The original brief explicitly names Tkinter/Listbox, so those two
technology requirements are not met by this edition. Task management,
persistence, priorities, deadlines, categories, sorting, and CSV export remain.
The previous Tkinter edition is separate and still available.
