import QtQuick
import QtQuick.Controls.Basic
import App

Button {
    id: lb

    property url linkUrl

    implicitHeight: 24
    topPadding: 0
    bottomPadding: 0
    leftPadding: 7
    rightPadding: 7

    HoverHandler { cursorShape: Qt.PointingHandCursor }

    AppToolTip {
        visible: lb.hovered && lb.text !== ""
        text: String(lb.linkUrl)
    }

    contentItem: Text {
        text: lb.text
        font.pixelSize: 12
        font.bold: true
        color: Theme.accent
        verticalAlignment: Text.AlignVCenter
        horizontalAlignment: Text.AlignHCenter
    }

    background: Rectangle {
        radius: 6
        color: lb.hovered ? (Theme.dark ? "#1d4ed8" : "#dbeafe") : Theme.accentSoftBg
        border.width: 1
        border.color: Theme.dark ? "#2563eb" : "#bfdbfe"
    }

    onClicked: Qt.openUrlExternally(linkUrl)
}
