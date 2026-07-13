import QtQuick
import App

Row {
    id: sb

    property string text: ""
    property string variant: "primary"   // primary | purple
    property bool enabledMain: true
    signal mainClicked()
    signal arrowClicked()

    height: 46

    readonly property color base: variant === "purple" ? Theme.purple : Theme.accent
    readonly property color hov: variant === "purple" ? Theme.purpleHover : Theme.accentHover
    readonly property color prs: variant === "purple" ? Theme.purplePressed : Theme.accentPressed
    readonly property color dis: variant === "purple" ? Theme.purpleDisabled : Theme.accentDisabled

    Rectangle {
        id: mainBtn
        width: mainLabel.implicitWidth + 28
        height: sb.height
        topLeftRadius: 7
        bottomLeftRadius: 7
        color: !sb.enabledMain ? sb.dis
             : (mainMouse.pressed ? sb.prs : (mainMouse.containsMouse ? sb.hov : sb.base))

        Text {
            id: mainLabel
            anchors.centerIn: parent
            text: sb.text
            color: Theme.textOnAccent
            opacity: sb.enabledMain ? 1.0 : 0.7
            font.pixelSize: Theme.fontSize
            font.bold: true
        }

        MouseArea {
            id: mainMouse
            anchors.fill: parent
            hoverEnabled: true
            enabled: sb.enabledMain
            cursorShape: Qt.PointingHandCursor
            onClicked: sb.mainClicked()
        }
    }

    Rectangle {
        id: arrowBtn
        width: 26
        height: sb.height
        topRightRadius: 7
        bottomRightRadius: 7
        color: !sb.enabledMain ? sb.dis
             : (arrowMouse.pressed ? sb.prs : (arrowMouse.containsMouse ? sb.hov : sb.base))

        Rectangle {
            width: 1
            height: parent.height
            color: Qt.rgba(1, 1, 1, 0.25)
        }

        Text {
            anchors.centerIn: parent
            text: "▾"
            color: Theme.textOnAccent
            opacity: sb.enabledMain ? 1.0 : 0.7
            font.pixelSize: 14
        }

        MouseArea {
            id: arrowMouse
            anchors.fill: parent
            hoverEnabled: true
            enabled: sb.enabledMain
            cursorShape: Qt.PointingHandCursor
            onClicked: sb.arrowClicked()
        }
    }
}
