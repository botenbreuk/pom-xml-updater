import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App
import "../controls"

Rectangle {
    id: rowDelegate

    required property string path
    required property string displayPath
    required property string projectName
    required property string ageText

    width: ListView.view ? ListView.view.width : implicitWidth
    height: 64
    radius: 10
    color: rowMouse.containsMouse ? Theme.accentSoftBg : Theme.surfaceAlt
    border.width: 1
    border.color: rowMouse.containsMouse ? (Theme.dark ? Theme.accent : "#bfdbfe") : Theme.border

    MouseArea {
        id: rowMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: Project.openFile(rowDelegate.path)
    }

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 12

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3

            Text {
                Layout.fillWidth: true
                text: rowDelegate.projectName
                font.pixelSize: Theme.fontSize
                font.bold: true
                color: Theme.textTable
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                text: rowDelegate.displayPath
                font.pixelSize: 13
                color: Theme.textSubtle
                elide: Text.ElideMiddle
            }
        }

        Text {
            text: rowDelegate.ageText
            font.pixelSize: 13
            color: Theme.textMuted
        }

        Button {
            id: removeBtn
            implicitWidth: 24
            implicitHeight: 24
            padding: 0
            HoverHandler { cursorShape: Qt.PointingHandCursor }

            AppToolTip {
                visible: removeBtn.hovered
                text: qsTr("Remove from recents")
            }

            contentItem: Text {
                text: "×"
                font.pixelSize: 16
                color: removeBtn.hovered ? Theme.danger : Theme.textMuted
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            background: Rectangle {
                radius: 4
                color: removeBtn.hovered ? (Theme.dark ? "#450a0a" : "#fee2e2") : "transparent"
            }

            onClicked: Project.removeRecent(rowDelegate.path)
        }
    }
}
