import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App
import "../controls"

Rectangle {
    id: frame

    color: Theme.surface
    radius: 10
    border.width: 1
    border.color: Theme.border
    clip: true

    readonly property real wSelect: 52
    readonly property real wGroup: 74
    readonly property real wCurrent: 150
    readonly property real wType: 110
    readonly property real wVer: 150
    readonly property bool mergeMode: App.mergePatchMinor

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 38
            color: Theme.surfaceAlt
            radius: frame.radius

            Rectangle {
                anchors.bottom: parent.bottom
                width: parent.width
                height: 1
                color: Theme.border
            }

            RowLayout {
                anchors.fill: parent
                spacing: 0

                Item {
                    Layout.preferredWidth: frame.wSelect
                    Layout.fillHeight: true
                    AppCheckBox {
                        anchors.centerIn: parent
                        checked: Project.headerChecked
                        enabled: !Project.isFetching && Project.selectableCount > 0
                        onToggled: Project.toggleSelectAll(!Project.headerChecked)
                    }
                }
                HeaderLabel { Layout.preferredWidth: frame.wGroup; text: qsTr("Group"); center: true }
                HeaderLabel { Layout.fillWidth: true; text: qsTr("Dependency"); leftInset: 10 }
                HeaderLabel { Layout.preferredWidth: frame.wCurrent; text: qsTr("Current"); center: true }
                HeaderLabel { Layout.preferredWidth: frame.wType; text: qsTr("Type"); center: true }
                HeaderLabel {
                    Layout.preferredWidth: frame.wVer
                    visible: !frame.mergeMode
                    text: qsTr("Patch ↑")
                    center: true
                }
                HeaderLabel {
                    Layout.preferredWidth: frame.wVer
                    text: frame.mergeMode ? qsTr("Minor / Patch ↑") : qsTr("Minor ↑")
                    center: true
                }
                HeaderLabel { Layout.preferredWidth: frame.wVer; text: qsTr("Major ↑"); center: true }
            }
        }

        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            reuseItems: true
            boundsBehavior: Flickable.StopAtBounds
            model: Project.dependencies

            ScrollBar.vertical: ThinScrollBar {}

            delegate: DependencyRow {
                width: ListView.view.width
                wSelect: frame.wSelect
                wGroup: frame.wGroup
                wCurrent: frame.wCurrent
                wType: frame.wType
                wVer: frame.wVer
                mergeMode: frame.mergeMode
            }

            Text {
                anchors.centerIn: parent
                visible: listView.count === 0 && Project.depCount > 0
                text: qsTr("All dependencies are up to date")
                font.pixelSize: Theme.fontSize
                color: Theme.textSubtle
            }
        }
    }
}
