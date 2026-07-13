import QtQuick
import QtQuick.Controls.Basic
import App

ToolButton {
    id: control

    property color accentColor: Theme.textBody

    font.pixelSize: Theme.fontSize
    topPadding: 6
    bottomPadding: 6
    leftPadding: 12
    rightPadding: 12

    HoverHandler {
        enabled: control.enabled
        cursorShape: Qt.PointingHandCursor
    }

    contentItem: Text {
        text: control.text
        font: control.font
        color: control.accentColor
        opacity: control.enabled ? 1.0 : 0.4
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: 6
        color: control.down ? Theme.toolbarPressed
                             : (control.hovered ? Theme.toolbarHover : "transparent")
    }
}
