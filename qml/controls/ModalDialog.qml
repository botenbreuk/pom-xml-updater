import QtQuick
import QtQuick.Layouts
import App

Item {
    id: modal
    anchors.fill: parent
    visible: active
    z: 2000

    property bool active: false
    property string title: ""
    property string message: ""
    property bool showCancel: false
    property string confirmText: qsTr("OK")
    property bool danger: false

    signal accepted()
    signal rejected()

    function show(opts) {
        title = opts.title || ""
        message = opts.message || ""
        showCancel = opts.showCancel === true
        confirmText = opts.confirmText || qsTr("OK")
        danger = opts.danger === true
        active = true
    }

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.55
        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 460
        implicitHeight: col.implicitHeight + 48
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.border

        ColumnLayout {
            id: col
            anchors.fill: parent
            anchors.margins: 24
            spacing: 12

            Text {
                Layout.fillWidth: true
                text: modal.title
                font.pixelSize: 18
                font.bold: true
                color: Theme.textHeading
                wrapMode: Text.WordWrap
            }

            Text {
                Layout.fillWidth: true
                text: modal.message
                font.pixelSize: Theme.fontSize
                color: Theme.textMuted
                wrapMode: Text.WordWrap
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.topMargin: 4
                spacing: 8

                Item { Layout.fillWidth: true }

                AppButton {
                    visible: modal.showCancel
                    variant: "ghost"
                    text: qsTr("Cancel")
                    Layout.preferredHeight: 40
                    onClicked: {
                        modal.active = false
                        modal.rejected()
                    }
                }

                AppButton {
                    variant: modal.danger ? "danger" : "primary"
                    text: modal.confirmText
                    Layout.preferredHeight: 40
                    onClicked: {
                        modal.active = false
                        modal.accepted()
                    }
                }
            }
        }
    }
}
