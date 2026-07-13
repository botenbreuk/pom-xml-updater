import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import QtQuick.Dialogs
import App
import "controls"
import "components"
import "screens"

ApplicationWindow {
    id: root

    visible: true
    width: 1280
    height: 720
    minimumWidth: 1000
    minimumHeight: 600
    title: qsTr("Pom.xml Updater")
    color: Theme.window

    property bool versionsReady: false
    property bool settingsOpen: false
    property bool hardRefresh: false
    property bool installVisible: false
    property string pendingUpdateMode: ""
    property string pendingAction: ""
    readonly property string view: settingsOpen ? "settings"
                                                 : (Project.hasFile ? "table" : "start")

    Component.onCompleted: Theme.dark = Qt.binding(() => App.dark)

    Connections {
        target: App
        function onVersionsChanged() {
            root.versionsReady = true
            Git.setJavaVersion(App.javaVersion)
        }
        function onFlash(message) { flashMsg.show(message) }
    }

    Connections {
        target: Git
        function onReloadRequested() { Project.reopen() }
        function onPullFailed(message) {
            root.pendingAction = ""
            modal.show({ "title": qsTr("git pull failed"), "message": message })
        }
    }

    Connections {
        target: Project
        function onOpenError(title, body) {
            root.pendingAction = ""
            modal.show({ "title": title, "message": body })
        }
        function onInfoMessage(title, body) {
            root.pendingAction = ""
            modal.show({ "title": title, "message": body })
        }
        function onConfirmUpdateAll(count, label, mode) {
            root.pendingUpdateMode = mode
            root.pendingAction = "updateAll"
            modal.show({
                "title": qsTr("Confirm Update All"),
                "message": qsTr("Update %1 dependenc(ies) using mode: %2?\nThis will overwrite your pom.xml.").arg(count).arg(label),
                "showCancel": true,
                "confirmText": qsTr("Update")
            })
        }
        function onHasFileChanged() { Git.setProject(Project.projectDir) }
    }

    Connections {
        target: Install
        function onSucceeded() { Project.clearPending() }
    }

    Connections {
        target: BuildTool
        function onShowPicker(currentId) { toolDialog.open(currentId) }
    }

    Shortcut {
        sequences: [StandardKey.Refresh]
        enabled: Project.hasFile
        onActivated: Project.startRefresh(root.hardRefresh)
    }

    header: ToolBar {
        implicitHeight: 46

        background: Rectangle {
            color: Theme.toolbarBg
            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.border
            }
        }

        contentItem: Item {

        RowLayout {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.verticalCenter: parent.verticalCenter
            anchors.leftMargin: 14
            anchors.rightMargin: 14
            spacing: 2

            AppToolButton {
                text: qsTr("←  Back")
                visible: root.settingsOpen
                onClicked: root.settingsOpen = false
            }

            Text {
                visible: root.settingsOpen
                text: qsTr("Settings")
                color: Theme.textHeading
                font.pixelSize: 15
                font.bold: true
                leftPadding: 4
            }

            AppToolButton {
                text: qsTr("📂  Open pom.xml")
                visible: !root.settingsOpen && !Project.hasFile
                onClicked: fileDialog.open()
            }

            AppToolButton {
                text: qsTr("📁  Open Folder")
                visible: !root.settingsOpen && !Project.hasFile
                onClicked: folderDialog.open()
            }

            Row {
                visible: !root.settingsOpen && Project.hasFile
                spacing: 0

                AppToolButton {
                    text: root.hardRefresh ? qsTr("↺  Hard Refresh") : qsTr("↺  Refresh")
                    enabled: !Project.isFetching
                    onClicked: Project.startRefresh(root.hardRefresh)
                }
                AppToolButton {
                    text: "▾"
                    onClicked: refreshMenu.popup()
                }
            }

            AppToolButton {
                text: qsTr("⚙  Settings")
                visible: !root.settingsOpen
                onClicked: {
                    settingsPage.syncFromSettings()
                    root.settingsOpen = true
                }
            }

            Item { Layout.fillWidth: true }

            Row {
                Layout.alignment: Qt.AlignVCenter
                visible: !root.settingsOpen && Project.hasFile && Git.hasRepo
                spacing: 8

                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    height: 24
                    width: branchText.implicitWidth + 16
                    radius: 5
                    readonly property bool warn: Git.behind > 0 && !Git.fetching
                    color: Git.fetching ? Theme.surfaceMuted
                         : (warn ? (Theme.dark ? "#451a03" : "#fef9c3")
                                 : (Theme.dark ? "#14532d" : "#dcfce7"))
                    border.width: 1
                    border.color: Git.fetching ? Theme.border
                                : (warn ? (Theme.dark ? "#b45309" : "#fcd34d")
                                        : (Theme.dark ? "#166534" : "#86efac"))

                    Text {
                        id: branchText
                        anchors.centerIn: parent
                        text: "⎇ " + Git.branch + (Git.behind > 0 ? "  ↓" + Git.behind : "")
                        font.pixelSize: 13
                        font.bold: true
                        color: Git.fetching ? Theme.textMuted
                             : (parent.warn ? (Theme.dark ? "#fcd34d" : "#92400e")
                                            : (Theme.dark ? "#4ade80" : "#15803d"))
                    }
                }

                Rectangle {
                    anchors.verticalCenter: parent.verticalCenter
                    visible: Git.behind > 0 && !Git.fetching
                    height: 24
                    width: pullText.implicitWidth + 20
                    radius: 5
                    opacity: Git.pulling ? 0.6 : 1
                    color: pullMouse.containsMouse ? (Theme.dark ? "#1d4ed8" : "#dbeafe")
                                                   : (Theme.dark ? "#1e3a5f" : "#eff6ff")
                    border.width: 1
                    border.color: Theme.dark ? "#2563eb" : "#93c5fd"

                    Text {
                        id: pullText
                        anchors.centerIn: parent
                        text: Git.pulling ? qsTr("Pulling…") : qsTr("↓ Pull")
                        font.pixelSize: 13
                        font.bold: true
                        color: Theme.dark ? "#93c5fd" : "#2563eb"
                    }

                    MouseArea {
                        id: pullMouse
                        anchors.fill: parent
                        hoverEnabled: true
                        enabled: !Git.pulling
                        cursorShape: Qt.PointingHandCursor
                        onClicked: Git.pull()
                    }
                }
            }

            Rectangle {
                id: toolBadge
                Layout.alignment: Qt.AlignVCenter
                visible: !root.settingsOpen && Project.hasFile
                height: 26
                width: toolRow.implicitWidth + 20
                radius: 6
                color: toolMouse.containsMouse ? Theme.toolbarHover : Theme.surfaceMuted
                border.width: 1
                border.color: Theme.border

                Row {
                    id: toolRow
                    anchors.centerIn: parent
                    spacing: 6

                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "🪶"
                        font.pixelSize: 12
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: BuildTool.activeName
                        font.pixelSize: 13
                        font.bold: true
                        color: Theme.textBody
                    }
                    Text {
                        anchors.verticalCenter: parent.verticalCenter
                        text: BuildTool.hasOverride ? "📌" : "▾"
                        font.pixelSize: 11
                        color: Theme.textSubtle
                    }
                }

                MouseArea {
                    id: toolMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: BuildTool.requestPicker()
                }
            }

            AppToolButton {
                text: qsTr("✕  Close")
                visible: !root.settingsOpen && Project.hasFile
                accentColor: Theme.danger
                onClicked: Project.closeFile()
            }
        }
        }
    }

    AppMenu {
        id: refreshMenu
        AppMenuItem { text: qsTr("↺  Refresh"); onTriggered: root.hardRefresh = false }
        AppMenuItem { text: qsTr("↺  Hard Refresh"); onTriggered: root.hardRefresh = true }
    }

    StackLayout {
        anchors.fill: parent
        currentIndex: root.view === "start" ? 0 : (root.view === "table" ? 1 : 2)

        StartScreen {
            onOpenFileRequested: fileDialog.open()
            onOpenFolderRequested: folderDialog.open()
        }

        ProjectView {
            onResolveRequested: {
                Install.start(Project.projectDir)
                root.installVisible = true
            }
        }

        SettingsPage {
            id: settingsPage
            onClearCacheRequested: {
                root.pendingAction = "clearCache"
                modal.show({
                    "title": qsTr("Clear cache?"),
                    "message": qsTr("All locally stored version data will be deleted. The next time you open a project every dependency will be re-fetched from Maven Central."),
                    "showCancel": true,
                    "confirmText": qsTr("Clear Cache"),
                    "danger": true
                })
            }
        }
    }

    Loader {
        anchors.fill: parent
        active: root.installVisible
        sourceComponent: Component {
            InstallOverlay {
                onClosed: root.installVisible = false
            }
        }
    }

    FlashMessage { id: flashMsg }

    footer: Rectangle {
        implicitHeight: 30
        color: Theme.statusBg

        Rectangle {
            anchors.top: parent.top
            width: parent.width
            height: 1
            color: Theme.border
        }

        RowLayout {
            anchors.fill: parent
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            spacing: 10

            Text {
                // Flexes and elides so the trailing version chips always fit.
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                text: Project.statusMessage !== "" ? Project.statusMessage
                    : (Project.hasFile ? "" : qsTr("No file loaded. Open a pom.xml to begin."))
                font.pixelSize: 14
                color: Theme.statusText
                elide: Text.ElideRight
            }

            Text {
                visible: Project.hasFile
                Layout.maximumWidth: 300
                Layout.minimumWidth: 0
                text: Project.filePath
                font.pixelSize: 13
                color: Theme.textSubtle
                elide: Text.ElideLeft
            }

            Text {
                visible: Git.javaHintText !== ""
                Layout.minimumWidth: implicitWidth
                text: Git.javaHintText
                font.pixelSize: 13
                font.bold: true
                color: Git.javaHintWarn ? Theme.warn : Theme.textMuted
            }

            Text {
                visible: Git.javaHintText !== ""
                text: "·"
                font.pixelSize: 13
                color: Theme.textSubtle
            }

            Text {
                Layout.minimumWidth: implicitWidth
                text: !root.versionsReady ? qsTr("java …")
                    : (App.javaVersion ? qsTr("java %1").arg(App.javaVersion) : qsTr("java —"))
                font.pixelSize: 13
                color: Theme.statusText
            }

            Text {
                text: "·"
                font.pixelSize: 13
                color: Theme.textSubtle
            }

            Text {
                Layout.minimumWidth: implicitWidth
                text: qsTr("%1 %2").arg(BuildTool.activeName)
                    .arg((root.versionsReady && App.toolVersion) ? App.toolVersion : "…")
                font.pixelSize: 13
                color: Theme.statusText
            }
        }
    }

    FileDialog {
        id: fileDialog
        title: qsTr("Open pom.xml")
        currentFolder: Project.initialFileDir
        nameFilters: [qsTr("pom.xml (pom.xml *.pom)"), qsTr("All files (*)")]
        onAccepted: Project.openFileUrl(selectedFile)
    }

    FolderDialog {
        id: folderDialog
        title: qsTr("Open Folder containing pom.xml")
        currentFolder: Project.initialFolderDir
        onAccepted: Project.openFolderUrl(selectedFolder)
    }

    BuildToolDialog { id: toolDialog }

    ModalDialog {
        id: modal
        onAccepted: {
            if (root.pendingAction === "updateAll")
                Project.applyUpdateAll(root.pendingUpdateMode)
            else if (root.pendingAction === "clearCache")
                App.clearCache()
            root.pendingAction = ""
        }
        onRejected: root.pendingAction = ""
    }
}
