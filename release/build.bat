@echo off
setlocal

set SCRIPT_DIR=%~dp0
set PROJECT_ROOT=%SCRIPT_DIR%..

echo === Pom.xml Updater Build ===
echo Project root: %PROJECT_ROOT%

echo.
echo --- Installing build dependencies ---
pip install pyinstaller
if errorlevel 1 goto :error

if not exist "%SCRIPT_DIR%icons\icon.ico" (
    echo.
    echo --- Converting icons ---
    pip install Pillow cairosvg
    if errorlevel 1 goto :error
    python "%SCRIPT_DIR%convert_icon.py"
    if errorlevel 1 goto :error
) else (
    echo.
    echo --- Icons already present, skipping conversion ---
)

echo.
echo --- Running PyInstaller ---
pyinstaller "%SCRIPT_DIR%pom_xml_updater.spec" ^
    --distpath "%PROJECT_ROOT%\dist" ^
    --workpath "%PROJECT_ROOT%\build" ^
    --noconfirm
if errorlevel 1 goto :error

echo.
echo === Build Complete ===
if exist "%PROJECT_ROOT%\dist\PomXmlUpdater.exe" (
    echo Output: %PROJECT_ROOT%\dist\PomXmlUpdater.exe
) else (
    echo Error: Expected output not found
    goto :error
)

goto :eof

:error
echo Build failed!
exit /b 1
