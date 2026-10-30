import QtQuick
import QtQuick.Layouts
import App

Item {
    id: h

    property string text: ""
    property bool center: false
    property real leftInset: 0
    property string resizeEdge: ""   // left | right: edge with the drag grip; "" keeps the width fixed
    property real spareWidth: 0      // how much wider a drag may make the column

    // Narrowest a drag can make the column: fits the header text and the usual cell
    // badges and versions. Columns with wider cells set a larger value, or raise it
    // through cellMinWidth when the width their cells need varies.
    property real cellMinWidth: 0
    property real minWidth: Math.max(72, label.implicitWidth + 24, cellMinWidth)

    signal resized(real width)
    signal resizeFinished()

    Layout.fillHeight: true

    Text {
        id: label
        anchors.verticalCenter: parent.verticalCenter
        anchors.horizontalCenter: h.center ? parent.horizontalCenter : undefined
        anchors.left: h.center ? undefined : parent.left
        anchors.leftMargin: h.center ? 0 : h.leftInset
        text: h.text
        font.pixelSize: 13
        font.bold: true
        color: Theme.textMuted
        elide: Text.ElideRight
    }

    MouseArea {
        id: grip

        property real pressX: 0
        property real pressWidth: 0
        property real maxWidth: 0

        visible: h.resizeEdge !== ""
        x: (h.resizeEdge === "left" ? 0 : h.width) - grip.width / 2
        width: 8
        height: h.height
        hoverEnabled: true
        cursorShape: Qt.SplitHCursor

        // Scene coordinates: the grip itself moves with the edge it drags.
        onPressed: (mouse) => {
            pressX = mapToItem(null, mouse.x, 0).x
            pressWidth = h.width
            maxWidth = h.width + h.spareWidth
        }
        onPositionChanged: (mouse) => {
            if (!pressed)
                return
            const dx = mapToItem(null, mouse.x, 0).x - pressX
            const w = pressWidth + (h.resizeEdge === "left" ? -dx : dx)
            h.resized(Math.round(Math.max(h.minWidth, Math.min(w, maxWidth))))
        }
        onReleased: h.resizeFinished()

        Rectangle {
            anchors.centerIn: parent
            width: 1
            height: 16
            color: grip.pressed || grip.containsMouse ? Theme.accent : Theme.border
        }
    }
}
