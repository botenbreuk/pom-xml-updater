# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Pom.xml Updater."""
import re
import sys
from pathlib import Path

block_cipher = None

PROJECT_ROOT = Path(SPECPATH).parent
RELEASE_DIR = PROJECT_ROOT / "release"

VERSION = re.search(
    r'VERSION\s*=\s*"([^"]+)"',
    (PROJECT_ROOT / "_version.py").read_text(),
).group(1)

if sys.platform == "darwin":
    icon_file = str(RELEASE_DIR / "icons" / "icon.icns")
elif sys.platform == "win32":
    icon_file = str(RELEASE_DIR / "icons" / "icon.ico")
else:
    icon_file = str(RELEASE_DIR / "icons" / "icon.png")

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=[
        (str(PROJECT_ROOT / "assets"), "assets"),
        (str(PROJECT_ROOT / "qml"), "qml"),
    ],
    hiddenimports=[
        "_version",
        "core",
        "core.maven_central",
        "core.version_cache",
        "core.pom_xml",
        "core.maven_versions",
        "core.build_tool",
        "core.java_env",
        "core.m2_repo",
        "core.git_info",
        "models",
        "models.dependency",
        "models.settings",
        "app",
        "app.app_controller",
        "app.project_controller",
        "app.install_controller",
        "app.build_tool_controller",
        "app.git_controller",
        "app.dependency_model",
        "app.recent_files_model",
        "workers",
        "workers.fetch_worker",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.QtSvg",
        "PyQt6.QtQml",
        "PyQt6.QtQuick",
        "PyQt6.QtQuickControls2",
        "requests",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == "darwin":
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="PomXmlUpdater",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_file,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name="PomXmlUpdater",
    )

    app = BUNDLE(
        coll,
        name="PomXmlUpdater.app",
        icon=icon_file,
        bundle_identifier="nl.42.pom-xml-updater",
        info_plist={
            "CFBundleDisplayName": "Pom.xml Updater",
            "CFBundleShortVersionString": VERSION,
            "CFBundleIconFile": "icon.icns",
            "NSHighResolutionCapable": True,
        },
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name="PomXmlUpdater",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        runtime_tmpdir=None,
        console=False,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
        icon=icon_file,
    )
