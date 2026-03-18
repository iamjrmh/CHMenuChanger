@echo off
setlocal enabledelayedexpansion

:: ── Keep window open if double-clicked ─────────────────────────────────────
if not defined _RELAUNCHED (
    set _RELAUNCHED=1
    cmd /k ""%~f0""
    exit /b
)

title CHMenuChanger Builder
cd /d "%~dp0"

echo.
echo  =============================================================
echo   CHMenuChanger -- Automated Build Script
echo  =============================================================
echo.

:: ── Sanity checks ────────────────────────────────────────────────────────────
if not exist "clone_hero_bg_changer.py" (
    echo  [ERROR] clone_hero_bg_changer.py not found in this folder.
    echo  Make sure build.bat, write_spec.py, and rthook_texture2d.py are
    echo  all in the same folder as clone_hero_bg_changer.py.
    goto :fail
)

if not exist "write_spec.py" (
    echo  [ERROR] write_spec.py not found in this folder.
    goto :fail
)

if not exist "rthook_texture2d.py" (
    echo  [ERROR] rthook_texture2d.py not found in this folder.
    goto :fail
)

:: ── [1/7] Locate Python 3.11 ─────────────────────────────────────────────────
echo  [1/7] Locating Python 3.11...

set "PYTHON="

py -3.11 --version >nul 2>&1
if !errorlevel! == 0 ( set "PYTHON=py -3.11" & goto :found_python )

python3.11 --version >nul 2>&1
if !errorlevel! == 0 ( set "PYTHON=python3.11" & goto :found_python )

for %%P in (
    "C:\Python311\python.exe"
    "C:\Program Files\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) do (
    if exist %%P ( set "PYTHON=%%~P" & goto :found_python )
)

python --version 2>&1 | findstr "3.11" >nul
if !errorlevel! == 0 ( set "PYTHON=python" & goto :found_python )

echo  [ERROR] Python 3.11 not found on this machine.
echo  Download: https://www.python.org/downloads/release/python-3119/
echo  During install: check "Add Python to PATH"
goto :fail

:found_python
echo  Found: %PYTHON%
%PYTHON% --version
echo.

:: ── [2/7] Create virtual environment ─────────────────────────────────────────
echo  [2/7] Setting up virtual environment (.venv)...

if exist ".venv" (
    echo  .venv already exists -- skipping creation.
) else (
    %PYTHON% -m venv .venv
    if !errorlevel! neq 0 ( echo  [ERROR] venv creation failed. & goto :fail )
    echo  .venv created.
)

call ".venv\Scripts\activate.bat"
if !errorlevel! neq 0 ( echo  [ERROR] Could not activate .venv. & goto :fail )
echo  Activated: %VIRTUAL_ENV%
echo.

:: ── [3/7] Install dependencies ────────────────────────────────────────────────
echo  [3/7] Installing dependencies (this may take a minute)...

python -m pip install --upgrade pip setuptools wheel
if !errorlevel! neq 0 ( echo  [ERROR] pip upgrade failed. & goto :fail )

pip install "Pillow==10.4.0"
if !errorlevel! neq 0 ( echo  [ERROR] Pillow install failed. & goto :fail )

pip install "UnityPy==1.25.0"
if !errorlevel! neq 0 ( echo  [ERROR] UnityPy install failed. & goto :fail )

pip install brotli brotlicffi lz4 texture2ddecoder
if !errorlevel! neq 0 ( echo  [ERROR] Native dependency install failed. & goto :fail )

pip install "pyinstaller==6.10.0"
if !errorlevel! neq 0 ( echo  [ERROR] PyInstaller install failed. & goto :fail )

echo.
echo  All dependencies installed.
echo.

:: ── [4/7] Verify critical imports ────────────────────────────────────────────
echo  [4/7] Verifying critical imports...

python -c "import UnityPy; print('  UnityPy          OK  v' + UnityPy.__version__)"
if !errorlevel! neq 0 ( echo  [ERROR] UnityPy import failed. & goto :fail )

python -c "import texture2ddecoder; print('  texture2ddecoder OK')"
if !errorlevel! neq 0 ( echo  [ERROR] texture2ddecoder import failed. & goto :fail )

python -c "import lz4.block; print('  lz4.block        OK')"
if !errorlevel! neq 0 ( echo  [ERROR] lz4 import failed. & goto :fail )

python -c "from PIL import Image; print('  Pillow           OK  v' + Image.__version__)"
if !errorlevel! neq 0 ( echo  [ERROR] Pillow import failed. & goto :fail )

echo.

:: ── [5/7] Write spec file ─────────────────────────────────────────────────────
echo  [5/7] Writing CHMenuChanger.spec...

python write_spec.py
if !errorlevel! neq 0 ( echo  [ERROR] write_spec.py failed. & goto :fail )

if not exist "CHMenuChanger.spec" (
    echo  [ERROR] CHMenuChanger.spec was not created.
    goto :fail
)
echo.

:: ── [6/7] Clean old build artifacts ──────────────────────────────────────────
echo  [6/7] Cleaning previous build and dist folders...

if exist "build" ( rmdir /s /q "build" && echo  Removed: build\ )
if exist "dist"  ( rmdir /s /q "dist"  && echo  Removed: dist\  )
echo.

:: ── [7/7] Run PyInstaller ─────────────────────────────────────────────────────
echo  [7/7] Running PyInstaller (takes 1-3 minutes, output below)...
echo  ---------------------------------------------------------
echo.

pyinstaller CHMenuChanger.spec
if !errorlevel! neq 0 (
    echo.
    echo  ---------------------------------------------------------
    echo  [ERROR] PyInstaller failed. Read the output above.
    echo.
    echo  Common causes:
    echo    - "ModuleNotFoundError" : a hidden import is missing
    echo    - "collect_all" error   : a package failed to install
    echo    - Antivirus blocked a write into dist\
    echo.
    goto :fail
)

:: ── Done ─────────────────────────────────────────────────────────────────────
echo.
echo  =============================================================
echo   BUILD SUCCESSFUL
echo  =============================================================
echo.
echo   Executable : dist\CHMenuChanger\CHMenuChanger.exe
echo   Full bundle: dist\CHMenuChanger\
echo.
echo   ZIP the entire dist\CHMenuChanger\ folder to distribute.
echo   Do NOT ship the .exe alone -- it needs _internal\ beside it.
echo.
echo   Test now: run dist\CHMenuChanger\CHMenuChanger.exe from this window.
echo   If it crashes silently, the error will print here.
echo.
:: NSIS installer build (optional)
echo.
echo  [Optional] Looking for NSIS to build installer...

set "MAKENSIS="
if exist "C:\Program Files (x86)\NSIS\makensis.exe" set "MAKENSIS=C:\Program Files (x86)\NSIS\makensis.exe"
if exist "C:\Program Files\NSIS\makensis.exe" set "MAKENSIS=C:\Program Files\NSIS\makensis.exe"

if not defined MAKENSIS (
    echo  NSIS not found -- skipping installer.
    echo  Install from https://nsis.sourceforge.io/Download then rerun to get CHMenuChanger_Setup.exe
    goto :done_nsis
)

if not exist "CHMenuChanger_Installer.nsi" (
    echo  CHMenuChanger_Installer.nsi not found -- skipping installer.
    goto :done_nsis
)

echo  Compiling NSIS installer...
"%MAKENSIS%" CHMenuChanger_Installer.nsi
if !errorlevel! neq 0 (
    echo  [WARNING] NSIS compile failed. .exe build is still good.
    goto :done_nsis
)
echo  Installer built: CHMenuChanger_Setup.exe

:done_nsis
echo.
echo  =============================================================
echo   BUILD SUCCESSFUL
echo  =============================================================
echo.
echo   Executable : dist\CHMenuChanger\CHMenuChanger.exe
echo   Installer  : CHMenuChanger_Setup.exe  (if NSIS was installed)
echo.
echo   Without installer: ZIP the entire dist\CHMenuChanger\ folder.
echo   With installer:    ship CHMenuChanger_Setup.exe standalone.
echo.
echo   Test: run dist\CHMenuChanger\CHMenuChanger.exe from this window.
echo.
goto :eof

:fail
echo.
echo  Build did not complete. Fix the error above and run build.bat again.
echo.
