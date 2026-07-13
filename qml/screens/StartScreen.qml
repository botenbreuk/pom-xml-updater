import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App
import "../controls"
import "../components"

Item {
    id: startScreen

    Layout.fillWidth: true
    Layout.fillHeight: true

    signal openFileRequested()
    signal openFolderRequested()

    ColumnLayout {
        anchors.centerIn: parent
        width: Math.min(540, startScreen.width - 48)
        spacing: 0

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: "🪶"
            font.pixelSize: 48
        }

        Item { Layout.preferredHeight: 14 }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("Pom.xml Updater")
            font.pixelSize: 24
            font.bold: true
            color: Theme.textHeading
        }

        Item { Layout.preferredHeight: 6 }

        Text {
            Layout.alignment: Qt.AlignHCenter
            text: qsTr("Check and update your Maven dependencies")
            font.pixelSize: Theme.fontSize
            color: Theme.textMuted
        }

        Item { Layout.preferredHeight: 28 }

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: 10

            AppButton {
                variant: "secondary"
                text: qsTr("📁  Open Folder")
                Layout.minimumWidth: 150
                onClicked: startScreen.openFolderRequested()
            }

            AppButton {
                variant: "primary"
                text: qsTr("📄  Open pom.xml")
                Layout.minimumWidth: 180
                onClicked: startScreen.openFileRequested()
            }
        }

        Item { Layout.preferredHeight: 36 }

        RowLayout {
            Layout.fillWidth: true
            visible: Project.hasRecents

            Text {
                Layout.fillWidth: true
                text: qsTr("RECENT")
                font.pixelSize: 13
                font.bold: true
                color: Theme.textSubtle
            }

            Button {
                id: clearBtn
                text: qsTr("Clear all")
                padding: 2

                HoverHandler { cursorShape: Qt.PointingHandCursor }

                contentItem: Text {
                    text: clearBtn.text
                    font.pixelSize: 13
                    font.bold: true
                    color: clearBtn.hovered ? Theme.danger : Theme.textSubtle
                    verticalAlignment: Text.AlignVCenter
                }
                background: Item {}
                onClicked: Project.clearRecents()
            }
        }

        Item { Layout.preferredHeight: 8; visible: Project.hasRecents }

        ListView {
            id: recentList
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(contentHeight, 320)
            visible: Project.recentCount > 0
            clip: true
            spacing: 4
            boundsBehavior: Flickable.StopAtBounds
            model: Project.recentFiles
            delegate: RecentFileRow {}
            ScrollBar.vertical: ThinScrollBar {}
        }

        Text {
            Layout.fillWidth: true
            visible: Project.hasRecents && Project.recentCount === 0
            text: qsTr("No recent files.")
            font.pixelSize: Theme.fontSize
            color: Theme.textSubtle
            horizontalAlignment: Text.AlignHCenter
            topPadding: 20
            bottomPadding: 20
        }
    }
}
