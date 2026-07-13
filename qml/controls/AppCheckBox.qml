import QtQuick
import App

Item {
    id: cb

    property bool checked: false
    property string label: ""
    signal toggled()

    implicitHeight: 20
    implicitWidth: 20 + (label !== "" ? 7 + labelText.implicitWidth : 0)
    opacity: enabled ? 1.0 : 0.6

    Rectangle {
        id: box
        width: 20
        height: 20
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        radius: 4
        color: cb.checked ? Theme.accent : (cb.enabled ? Theme.surface : Theme.surfaceMuted)
        border.width: 2
        border.color: cb.checked ? Theme.accent : Theme.borderStrong

        Text {
            anchors.centerIn: parent
            visible: cb.checked
            text: "✓"
            color: Theme.textOnAccent
            font.pixelSize: 13
            font.bold: true
        }
    }

    Text {
        id: labelText
        visible: cb.label !== ""
        text: cb.label
        anchors.left: box.right
        anchors.leftMargin: 7
        anchors.verticalCenter: parent.verticalCenter
        color: Theme.textBody
        font.pixelSize: Theme.fontSize
    }

    MouseArea {
        anchors.fill: parent
        enabled: cb.enabled
        cursorShape: Qt.PointingHandCursor
        onClicked: cb.toggled()
    }
}
