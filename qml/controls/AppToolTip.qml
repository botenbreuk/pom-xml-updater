import QtQuick
import QtQuick.Controls.Basic
import App

ToolTip {
    id: tip
    padding: 6

    contentItem: Text {
        text: tip.text
        color: Theme.textTable
        font.pixelSize: 13
        wrapMode: Text.WordWrap
    }

    background: Rectangle {
        color: Theme.surface
        border.width: 1
        border.color: Theme.border
        radius: 6
    }
}
