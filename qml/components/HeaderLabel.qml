import QtQuick
import QtQuick.Layouts
import App

Item {
    id: h

    property string text: ""
    property bool center: false
    property real leftInset: 0

    Layout.fillHeight: true

    Text {
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
}
