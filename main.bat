@echo off
title BGET Toolkit
echo Starting the key listener script...

rem call locator (scripts\python_locator.bat should set PYTHON_PATH)
call "%~dp0src\python_locator.bat" %1
if errorlevel 1 (
	echo Could not obtain Python path.
	pause
	exit /b 1
)

echo Using Python: "%PYTHON_PATH%"
rem Tell poetry to use this Python for the project (will create or switch venv)
poetry env use "%PYTHON_PATH%"
poetry run python src/key_listener.py
pause