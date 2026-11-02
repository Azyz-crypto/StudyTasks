@echo off
setlocal
title StudyTasks
cd /d "%~dp0"

if not exist "app.py" goto missing_files
if not exist "requirements.txt" goto missing_files
if exist ".venv\Scripts\python.exe" goto check_dependencies

echo StudyTasks - first-time setup
echo Checking Python 3.13...
py -3.13 --version >nul 2>&1
if errorlevel 1 goto missing_python
echo Creating the project environment...
py -3.13 -m venv .venv
if errorlevel 1 goto setup_error

:check_dependencies
if not exist ".venv\requirements-installed.txt" goto install_dependencies
fc /b "requirements.txt" ".venv\requirements-installed.txt" >nul 2>&1
if errorlevel 1 goto install_dependencies
goto launch

:install_dependencies
echo Installing dependencies. Internet is needed for this first setup.
".venv\Scripts\python.exe" -m pip install -r "requirements.txt"
if errorlevel 1 goto setup_error
copy /y "requirements.txt" ".venv\requirements-installed.txt" >nul
if errorlevel 1 goto setup_error

:launch
echo.
echo Opening StudyTasks in your browser...
echo Keep this window open while using the application.
echo If the browser does not open, use the Local URL printed below.
echo Close this window when you are finished.
echo.
".venv\Scripts\python.exe" -m streamlit run "app.py"
if errorlevel 1 goto launch_error
exit /b 0

:missing_python
echo.
echo Python 3.13 was not found by the Windows Python launcher.
echo Install Python 3.13, using the Windows installer, then run START.bat again.
echo See START_HERE.txt for the official download link.
pause
exit /b 1

:missing_files
echo.
echo Extract the COMPLETE ZIP first. Keep START.bat beside app.py and requirements.txt.
pause
exit /b 1

:setup_error
echo.
echo Setup did not finish. Read the error above.
echo Check your internet connection, then run START.bat again.
echo If you moved this project folder, delete ONLY its .venv folder and retry.
echo Your saved tasks.json should be kept.
pause
exit /b 1

:launch_error
echo.
echo The app stopped. Read the error above before closing this window.
pause
exit /b 1
