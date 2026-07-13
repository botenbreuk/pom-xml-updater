import QtQuick
import App

Rectangle {
    id: badge

    property string label: ""
    property color bgColor: Theme.surfaceMuted
    property color fgColor: Theme.textMuted

    implicitWidth: text.implicitWidth + 16
    implicitHeight: 22
    radius: 5
    color: bgColor

    Text {
        id: text
        anchors.centerIn: parent
        text: badge.label
        color: badge.fgColor
        font.pixelSize: 11
        font.bold: true
    }
}
