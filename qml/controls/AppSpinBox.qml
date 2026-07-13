import QtQuick
import QtQuick.Layouts
import App

RowLayout {
    id: spin

    property int value: 0
    property int from: 0
    property int to: 100
    property string suffix: ""
    property string specialText: ""
    property var textFromValue: null
    property var computeNext: function(v) { return v + 1 }
    property var computePrev: function(v) { return v - 1 }
    property real boxWidth: 150

    spacing: 8

    function clamp(v) { return Math.max(spin.from, Math.min(spin.to, v)) }

    Rectangle {
        Layout.preferredWidth: 32
        Layout.preferredHeight: 38
        radius: 6
        color: minusMouse.pressed ? Theme.borderStrong : (minusMouse.containsMouse ? Theme.border : Theme.surfaceMuted)
        border.width: 1.5
        border.color: Theme.border
        Text { anchors.centerIn: parent; text: "−"; font.pixelSize: 18; font.bold: true; color: Theme.textBody }
        MouseArea {
            id: minusMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: spin.value = spin.clamp(spin.computePrev(spin.value))
        }
    }

    Rectangle {
        Layout.preferredWidth: spin.boxWidth
        Layout.preferredHeight: 38
        radius: 6
        color: Theme.surface
        border.width: 2
        border.color: Theme.border
        Text {
            anchors.centerIn: parent
            text: {
                if (spin.value === spin.from && spin.specialText !== "") return spin.specialText
                if (spin.textFromValue) return spin.textFromValue(spin.value)
                return spin.value + spin.suffix
            }
            color: Theme.textBody
            font.pixelSize: Theme.fontSize
        }
    }

    Rectangle {
        Layout.preferredWidth: 32
        Layout.preferredHeight: 38
        radius: 6
        color: plusMouse.pressed ? Theme.borderStrong : (plusMouse.containsMouse ? Theme.border : Theme.surfaceMuted)
        border.width: 1.5
        border.color: Theme.border
        Text { anchors.centerIn: parent; text: "+"; font.pixelSize: 18; font.bold: true; color: Theme.textBody }
        MouseArea {
            id: plusMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: spin.value = spin.clamp(spin.computeNext(spin.value))
        }
    }
}
