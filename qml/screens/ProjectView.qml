import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App
import "../controls"
import "../components"

Item {
    id: projectView

    Layout.fillWidth: true
    Layout.fillHeight: true

    signal resolveRequested()

    ColumnLayout {
        anchors.fill: parent
        anchors.leftMargin: 16
        anchors.rightMargin: 16
        anchors.topMargin: 12
        anchors.bottomMargin: 12
        spacing: 10

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 44
            radius: 8
            color: Theme.surface
            border.width: 1
            border.color: Theme.border

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 10
                spacing: 12

                Text {
                    text: qsTr("Show:")
                    font.pixelSize: 14
                    font.bold: true
                    color: Theme.textMuted
                }

                AppComboBox {
                    Layout.preferredWidth: 210
                    model: [qsTr("All groups"), "dependencies", "dependencyManagement", "plugins", "parent"]
                    values: ["", "dependencies", "dependencyManagement", "plugins", "parent"]
                    onValuePicked: (value) => Project.setFilterGroup(value)
                }

                AppCheckBox {
                    id: hideCb
                    label: qsTr("Hide up-to-date")
                    checked: Project.hideUptodateInitial
                    onToggled: {
                        checked = !checked
                        Project.setHideUptodate(checked)
                    }
                }

                Rectangle {
                    id: oldToggle
                    property bool active: false
                    implicitHeight: 30
                    implicitWidth: oldLabel.implicitWidth + 22
                    radius: 6
                    color: active ? (Theme.dark ? "#451a03" : "#fef9c3") : Theme.surfaceAlt
                    border.width: 1
                    border.color: active ? (Theme.dark ? "#b45309" : "#fcd34d") : Theme.border

                    Text {
                        id: oldLabel
                        anchors.centerIn: parent
                        text: qsTr("⚠  Old only")
                        font.pixelSize: 13
                        font.bold: oldToggle.active
                        color: oldToggle.active ? (Theme.dark ? "#fcd34d" : "#92400e") : Theme.textMuted
                    }

                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                    TapHandler {
                        onTapped: {
                            oldToggle.active = !oldToggle.active
                            Project.setOldOnly(oldToggle.active)
                        }
                    }
                }

                Item { Layout.fillWidth: true }

                Text {
                    text: Project.countSummary
                    font.pixelSize: 14
                    color: Theme.textMuted
                }
            }
        }

        DependencyTable {
            Layout.fillWidth: true
            Layout.fillHeight: true
        }

        ActionBar {
            Layout.fillWidth: true
            onResolveRequested: projectView.resolveRequested()
        }
    }
}
