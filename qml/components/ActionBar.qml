import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App
import "../controls"

ColumnLayout {
    id: actionBar

    property string mode: "patch_minor"
    readonly property string modeLabel: mode === "patch_minor" ? qsTr("Patch / Minor") : qsTr("All incl. Major")

    signal resolveRequested()

    spacing: 8

    Rectangle {
        Layout.fillWidth: true
        implicitHeight: 1
        color: Theme.border
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 8

        SplitButton {
            variant: "primary"
            text: qsTr("Update Selected  ·  %1").arg(actionBar.modeLabel)
            enabledMain: !Project.isFetching && Project.selectedCount > 0
            onMainClicked: Project.updateSelected(actionBar.mode)
            onArrowClicked: modeMenu.popup()
        }

        SplitButton {
            variant: "purple"
            text: qsTr("Update All  ·  %1").arg(actionBar.modeLabel)
            enabledMain: Project.canUpdateAll
            onMainClicked: Project.requestUpdateAll(actionBar.mode)
            onArrowClicked: modeMenu.popup()
        }

        Item { Layout.fillWidth: true }

        ProgressBar {
            id: progress
            visible: Project.isFetching
            Layout.preferredWidth: 180
            Layout.preferredHeight: 6
            from: 0
            to: 1
            value: Project.fetchProgress

            background: Rectangle { radius: 3; color: Theme.surfaceMuted }
            contentItem: Item {
                Rectangle {
                    width: progress.visualPosition * parent.width
                    height: parent.height
                    radius: 3
                    color: Theme.accent
                }
            }
        }

        AppButton {
            variant: "secondary"
            text: qsTr("🪶  %1").arg(BuildTool.installCommand)
            enabled: Project.hasFile
            Layout.preferredHeight: 46
            onClicked: actionBar.resolveRequested()
        }
    }

    AppMenu {
        id: modeMenu
        AppMenuItem { text: qsTr("Patch / Minor only"); onTriggered: actionBar.mode = "patch_minor" }
        AppMenuItem { text: qsTr("All (including Major)"); onTriggered: actionBar.mode = "all" }
    }
}
