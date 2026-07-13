import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App
import "../controls"

Item {
    id: overlay
    anchors.fill: parent

    signal closed()

    Rectangle {
        anchors.fill: parent
        color: "#000000"
        opacity: 0.55
        MouseArea { anchors.fill: parent }
    }

    Rectangle {
        anchors.centerIn: parent
        width: 720
        implicitHeight: cardCol.implicitHeight + 48
        radius: 12
        color: Theme.surface
        border.width: 1
        border.color: Theme.border

        ColumnLayout {
            id: cardCol
            anchors.fill: parent
            anchors.margins: 24
            spacing: 12

            Text {
                text: BuildTool.installCommand
                font.pixelSize: 18
                font.bold: true
                color: Theme.textHeading
            }

            ProgressBar {
                Layout.fillWidth: true
                Layout.preferredHeight: 6
                indeterminate: Install.running
                from: 0
                to: 1
                value: Install.running ? 0 : 1
                background: Rectangle { radius: 3; color: Theme.surfaceMuted }
            }

            Text {
                Layout.fillWidth: true
                text: Install.statusText
                wrapMode: Text.WordWrap
                font.pixelSize: Theme.fontSize
                font.bold: Install.status !== "running"
                color: Install.status === "ok" ? Theme.success
                     : (Install.status === "error" ? Theme.danger : Theme.textMuted)
            }

            Button {
                id: toggleBtn
                Layout.fillWidth: true
                checkable: true

                HoverHandler { cursorShape: Qt.PointingHandCursor }

                contentItem: Text {
                    text: (toggleBtn.checked ? "▼   " : "▶   ") + qsTr("Output")
                    color: Theme.textMuted
                    font.pixelSize: 14
                    font.bold: true
                    leftPadding: 8
                    verticalAlignment: Text.AlignVCenter
                }
                background: Rectangle {
                    radius: 6
                    color: toggleBtn.checked || toggleBtn.hovered ? Theme.surfaceMuted : Theme.surfaceAlt
                    border.width: 1
                    border.color: Theme.border
                }
            }

            ScrollView {
                visible: toggleBtn.checked
                Layout.fillWidth: true
                Layout.preferredHeight: 280
                clip: true
                ScrollBar.vertical: ThinScrollBar {}

                TextArea {
                    id: outArea
                    readOnly: true
                    text: Install.output
                    wrapMode: TextArea.NoWrap
                    color: "#e2e8f0"
                    font.family: Theme.monoFamily
                    font.pixelSize: 12
                    background: Rectangle {
                        color: Theme.dark ? "#020617" : "#0f172a"
                        radius: 6
                        border.width: 1
                        border.color: "#334155"
                    }
                    onTextChanged: cursorPosition = length
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Item { Layout.fillWidth: true }
                AppButton {
                    variant: "primary"
                    text: qsTr("Close")
                    enabled: !Install.running
                    Layout.preferredHeight: 40
                    onClicked: overlay.closed()
                }
            }
        }
    }

    Connections {
        target: Install
        function onStatusChanged() {
            if (Install.status === "error")
                toggleBtn.checked = true
        }
    }
}
