import QtQuick
import App

Rectangle {
    id: flash

    property string message: ""

    anchors.horizontalCenter: parent.horizontalCenter
    anchors.top: parent.top
    anchors.topMargin: 16
    z: 1000

    implicitWidth: label.implicitWidth + 40
    implicitHeight: 40
    radius: 20
    color: Theme.success
    opacity: 0
    visible: opacity > 0

    Text {
        id: label
        anchors.centerIn: parent
        text: flash.message
        color: "#ffffff"
        font.pixelSize: 14
        font.bold: true
    }

    function show(msg) {
        message = msg
        opacity = 1
        hideTimer.restart()
    }

    Timer {
        id: hideTimer
        interval: 1400
        onTriggered: fade.start()
    }

    OpacityAnimator {
        id: fade
        target: flash
        from: 1
        to: 0
        duration: 450
    }
}
