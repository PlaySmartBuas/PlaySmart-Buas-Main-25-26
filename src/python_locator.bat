@echo off
rem Locate project root (parent of scripts) and config file next to main.bat
set "ROOT=%~dp0.."
set "CONFIG_FILE=%ROOT%.python_path.txt"

if /I "%1"=="set" goto setpath

rem load saved path if present
if exist "%CONFIG_FILE%" (
  set /p PYTHON_PATH=<"%CONFIG_FILE%"
)

rem try where/py if nothing saved
if not defined PYTHON_PATH (
  for /f "usebackq delims=" %%i in (`where python 2^>nul`) do if not defined PYTHON_PATH set "PYTHON_PATH=%%i"
)
if not defined PYTHON_PATH (
  for /f "usebackq delims=" %%i in ('py -3 -c "import sys;print(sys.executable)" 2^>nul') do if not defined PYTHON_PATH set "PYTHON_PATH=%%i"
)

rem validate
if defined PYTHON_PATH (
  if not exist "%PYTHON_PATH%" set "PYTHON_PATH="
)

rem prompt and save if still not found
if not defined PYTHON_PATH (
  set /p PYTHON_PATH=Enter full path to python.exe: 
  if not exist "%PYTHON_PATH%" (
    echo Path "%PYTHON_PATH%" not found.
    exit /b 1
  )
  echo %PYTHON_PATH%>"%CONFIG_FILE%"
)

exit /b 0

:setpath
set /p PYTHON_PATH=Enter full path to python.exe: 
if not exist "%PYTHON_PATH%" (
  echo Path "%PYTHON_PATH%" not found.
  exit /b 1
)
echo %PYTHON_PATH%>"%CONFIG_FILE%"
exit /b 0