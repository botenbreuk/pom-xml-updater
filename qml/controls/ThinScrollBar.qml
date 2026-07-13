import QtQuick
import QtQuick.Controls.Basic
import App

ScrollBar {
    id: control
    policy: ScrollBar.AsNeeded
    minimumSize: 0.12

    contentItem: Rectangle {
        implicitWidth: 8
        implicitHeight: 8
        radius: 4
        opacity: control.size < 1.0 ? 1.0 : 0.0
        color: control.pressed || control.hovered
               ? (Theme.dark ? "#475569" : "#94a3b8")
               : (Theme.dark ? "#334155" : "#cbd5e1")
    }

    background: Item {}
}
