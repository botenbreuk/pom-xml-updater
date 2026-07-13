"""
Pom.xml Updater — desktop application entry point.

Runs the Qt Quick (QML) front-end.

Run with:
    python main.py [path/to/pom.xml]
"""
import os
import signal
import sys

# Make the project root importable from any working directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtQml import QQmlApplicationEngine
from PyQt6.QtWidgets import QApplication

from app.app_controller import AppController
from app.project_controller import ProjectController
from app.install_controller import InstallController
from app.git_controller import GitController
from app.build_tool_controller import BuildToolController
from core.version_cache import VersionCache
from models.settings import AppSettings
from _version import VERSION

# Resource root: the PyInstaller bundle dir when frozen, else the source tree.
_ROOT = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def main() -> None:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

    app = QApplication(sys.argv)
    app.setApplicationName("Pom.xml Updater")
    app.setOrganizationName("42nl")
    app.setApplicationVersion(VERSION)

    png_path = os.path.join(_ROOT, "release", "icons", "icon.png")
    pix = QPixmap(png_path)
    pix.setDevicePixelRatio(2.0)
    app.setWindowIcon(QIcon(pix))

    settings = AppSettings()
    settings.load()
    cache = VersionCache()

    app_controller = AppController(settings, cache)
    project_controller = ProjectController(settings, cache)
    install_controller = InstallController(settings)
    git_controller = GitController()
    bt_controller = BuildToolController(settings)

    # Settings changes flow App → Project (re-filter / re-fetch as needed).
    app_controller.displaySettingsChanged.connect(project_controller.applyDisplaySettings)
    app_controller.reFetchRequested.connect(project_controller.refetchForSettings)

    # The active build tool follows the open project; the status-bar version
    # follows the active build tool.
    project_controller.projectChanged.connect(
        lambda: bt_controller.setProject(project_controller.projectDir))
    bt_controller.activeChanged.connect(
        lambda: app_controller.refreshToolVersion(bt_controller.activeId,
                                                  bt_controller.projectDir))
    # Default / override edits in Settings re-resolve the open project's tool.
    app_controller.toolSettingsChanged.connect(bt_controller.reevaluate)
    # A pinned choice from the picker refreshes the Settings overrides list.
    bt_controller.overridesChanged.connect(app_controller.toolSettingsChanged)

    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    ctx.setContextProperty("App", app_controller)
    ctx.setContextProperty("Project", project_controller)
    ctx.setContextProperty("Install", install_controller)
    ctx.setContextProperty("Git", git_controller)
    ctx.setContextProperty("BuildTool", bt_controller)
    engine.addImportPath(os.path.join(_ROOT, "qml"))
    engine.load(QUrl.fromLocalFile(os.path.join(_ROOT, "qml", "Main.qml")))

    if not engine.rootObjects():
        sys.exit(1)

    app.aboutToQuit.connect(app_controller.shutdown)
    app.aboutToQuit.connect(project_controller.shutdown)
    app.aboutToQuit.connect(install_controller.shutdown)
    app.aboutToQuit.connect(git_controller.shutdown)

    # Allow passing a pom.xml path as a command-line argument.
    if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
        project_controller.openFile(os.path.abspath(sys.argv[1]))

    # Restore the OS default SIGINT handler so Ctrl+C terminates cleanly.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
