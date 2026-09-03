@echo off
chcp 65001 > nul
cls
echo ================================================================
echo   Universal Windows build: x86 + x64 + Inno Setup
echo ================================================================
echo.

where py >nul 2>&1
if errorlevel 1 (
    echo [ERROR] ไม่พบ Python Launcher ^(py.exe^)
    pause
    exit /b 1
)

py -3.8-32 -c "import sys; print(sys.version)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] ต้องติดตั้ง Python 3.8.10 แบบ 32-bit
    pause
    exit /b 1
)

py -3.8-64 -c "import sys; print(sys.version)" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] ต้องติดตั้ง Python 3.8.10 แบบ 64-bit
    pause
    exit /b 1
)

if not exist .build_venv_x86 py -3.8-32 -m venv .build_venv_x86
if errorlevel 1 goto :failed
if not exist .build_venv_x64 py -3.8-64 -m venv .build_venv_x64
if errorlevel 1 goto :failed

call .build_venv_x86\Scripts\python.exe -m pip install --upgrade "pip==25.0.1"
if errorlevel 1 goto :failed
call .build_venv_x86\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 goto :failed
call .build_venv_x86\Scripts\python.exe build_exe.py
if errorlevel 1 goto :failed

call .build_venv_x64\Scripts\python.exe -m pip install --upgrade "pip==25.0.1"
if errorlevel 1 goto :failed
call .build_venv_x64\Scripts\python.exe -m pip install -r requirements-build.txt
if errorlevel 1 goto :failed
call .build_venv_x64\Scripts\python.exe build_exe.py
if errorlevel 1 goto :failed

set ISCC="none"
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"

if %ISCC%=="none" (
    echo [ERROR] ต้องติดตั้ง Inno Setup 6.7.1
    pause
    exit /b 1
)

%ISCC% installer.iss
if errorlevel 1 goto :failed

echo.
echo [SUCCESS] dist_installer\BatteryRequisition_Setup_v1.0.0.exe
pause
exit /b 0

:failed
echo [ERROR] การ build ไม่สำเร็จ
pause
exit /b 1
