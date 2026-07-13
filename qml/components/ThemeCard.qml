import QtQuick
import App

Rectangle {
    id: card

    property string value: ""
    property string label: ""
    property bool selected: false
    signal picked(string value)

    implicitWidth: 240
    implicitHeight: col.implicitHeight + 24
    radius: 8
    color: selected ? Theme.accentSoftBg : Theme.surface
    border.width: selected ? 2 : 1
    border.color: selected ? Theme.accent : (cardHover.hovered ? Theme.borderStrong : Theme.border)

    HoverHandler { id: cardHover }

    Column {
        id: col
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.top: parent.top
        anchors.topMargin: 12
        spacing: 8

        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: card.label
            color: card.selected ? Theme.accentHover : Theme.textMuted
            font.pixelSize: 12
            font.bold: card.selected
        }

        MiniPreview { variant: card.value }
    }

    MouseArea {
        anchors.fill: parent
        cursorShape: Qt.PointingHandCursor
        onClicked: card.picked(card.value)
    }
}
