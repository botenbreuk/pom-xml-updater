import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App
import "../controls"

Item {
    id: cell

    property string rowId: ""
    property string version: ""
    property int ageDays: -1
    property string bumpType: "patch"   // patch | minor | major
    property string status: "none"      // loading | error | ok | none
    property string errorMsg: ""
    property real rightInset: 8

    function fmtAge(d) {
        if (d < 0) return ""
        if (d < 1) return "today"
        if (d < 30) return d + "d"
        if (d < 365) return Math.floor(d / 30) + "mo"
        return Math.floor(d / 365) + "y"
    }

    readonly property string ageText: fmtAge(ageDays)

    readonly property var btnColors: ({
        "patch": Theme.dark ? { bg: "#1e3a5f", hov: "#1d4ed8", fg: "#93c5fd", bd: "#2563eb" }
                            : { bg: "#dbeafe", hov: "#bfdbfe", fg: "#1d4ed8", bd: "#93c5fd" },
        "minor": Theme.dark ? { bg: "#14532d", hov: "#15803d", fg: "#86efac", bd: "#16a34a" }
                            : { bg: "#dcfce7", hov: "#bbf7d0", fg: "#15803d", bd: "#86efac" },
        "major": Theme.dark ? { bg: "#451a03", hov: "#92400e", fg: "#fcd34d", bd: "#b45309" }
                            : { bg: "#fef9c3", hov: "#fde68a", fg: "#92400e", bd: "#fcd34d" }
    })
    readonly property var bc: btnColors[bumpType] || btnColors["patch"]

    Text {
        visible: cell.status === "loading"
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        text: qsTr("Loading…")
        font.italic: true
        font.pixelSize: 14
        color: Theme.textSubtle
    }

    Text {
        id: errorText
        visible: cell.status === "error"
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        text: qsTr("Error")
        font.pixelSize: 14
        color: Theme.danger
        MouseArea { id: errorMouse; anchors.fill: parent; hoverEnabled: true }
        AppToolTip {
            visible: errorMouse.containsMouse && cell.errorMsg !== ""
            text: cell.errorMsg
        }
    }

    Text {
        visible: cell.status === "none" || (cell.status === "ok" && cell.version === "")
        anchors.left: parent.left
        anchors.leftMargin: 10
        anchors.verticalCenter: parent.verticalCenter
        text: "—"
        font.pixelSize: 16
        color: Theme.textFaint
    }

    RowLayout {
        visible: cell.status === "ok" && cell.version !== ""
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: cell.rightInset
        spacing: 6

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 1

            Text {
                Layout.fillWidth: true
                text: cell.version
                font.pixelSize: 14
                font.bold: true
                font.family: Theme.monoFamily
                color: Theme.textTable
                elide: Text.ElideRight
            }

            Text {
                visible: cell.ageText !== ""
                text: cell.ageText
                font.pixelSize: 13
                color: Theme.textMuted
            }
        }

        Rectangle {
            id: upBtn
            Layout.preferredWidth: 24
            Layout.preferredHeight: 24
            radius: 6
            color: upMouse.containsMouse ? cell.bc.hov : cell.bc.bg
            border.width: 1.5
            border.color: cell.bc.bd

            Text {
                anchors.centerIn: parent
                text: "↑"
                font.pixelSize: 16
                font.bold: true
                color: cell.bc.fg
            }

            MouseArea {
                id: upMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: Project.updateSingle(cell.rowId, cell.version)
            }

            AppToolTip {
                visible: upMouse.containsMouse
                text: qsTr("Update to %1").arg(cell.version)
            }
        }
    }
}
