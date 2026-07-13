import QtQuick
import QtQuick.Controls.Basic
import App

ComboBox {
    id: combo

    property var values: []
    signal valuePicked(var value)

    implicitHeight: 34
    font.pixelSize: Theme.fontSize

    HoverHandler { cursorShape: Qt.PointingHandCursor }

    contentItem: Text {
        text: combo.displayText
        font: combo.font
        color: Theme.textBody
        leftPadding: 10
        rightPadding: 28
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    indicator: Text {
        text: "▾"
        color: Theme.textMuted
        font.pixelSize: 12
        anchors.right: parent.right
        anchors.rightMargin: 10
        anchors.verticalCenter: parent.verticalCenter
    }

    background: Rectangle {
        radius: 6
        color: Theme.surface
        border.width: 1
        border.color: combo.activeFocus ? Theme.accent : Theme.border
    }

    delegate: ItemDelegate {
        id: itemDelegate
        required property int index
        required property string modelData
        width: combo.width
        height: 32
        contentItem: Text {
            text: itemDelegate.modelData
            font.pixelSize: Theme.fontSize
            color: Theme.textBody
            leftPadding: 8
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            color: combo.highlightedIndex === itemDelegate.index ? Theme.accentSoftBg : "transparent"
        }
    }

    popup: Popup {
        y: combo.height + 2
        width: combo.width
        implicitHeight: Math.min(contentItem.implicitHeight + 2, 320)
        padding: 1

        background: Rectangle {
            radius: 6
            color: Theme.surface
            border.width: 1
            border.color: Theme.border
        }

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: combo.popup.visible ? combo.delegateModel : null
            currentIndex: combo.highlightedIndex
            ScrollBar.vertical: ThinScrollBar {}
        }
    }

    onActivated: (i) => combo.valuePicked(combo.values[i])
}
