import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App
import "../controls"

Rectangle {
    id: row

    // ── model roles ────────────────────────────────────────────────────────
    required property int index
    required property string rowId
    required property string name
    required property string propertyName
    required property string group
    required property string groupLabel
    required property string rawConstraint
    required property string currentVersion
    required property string constraintType
    required property string constraintTypeLabel
    required property int currentAge
    required property bool needsInstall
    required property string repoUrl
    required property string repoLabel
    required property string centralUrl
    required property string fetchStatus
    required property string errorMessage
    required property string patchVersion
    required property string minorVersion
    required property string majorVersion
    required property int patchAge
    required property int minorAge
    required property int majorAge
    required property bool selected
    required property bool selectable

    // ── column metrics (set by the ListView delegate) ───────────────────────
    property real wSelect: 52
    property real wGroup: 74
    property real wCurrent: 150
    property real wType: 110
    property real wVer: 150
    property bool mergeMode: false

    implicitHeight: 52
    color: rowHover.hovered ? Theme.accentSoftBg : (index % 2 ? Theme.surfaceAlt : Theme.surface)

    HoverHandler { id: rowHover }

    readonly property bool isLoading: fetchStatus === "loading" || fetchStatus === "pending"
    readonly property bool isError: fetchStatus === "error"

    readonly property string minorCellVer: mergeMode ? (minorVersion !== "" ? minorVersion : patchVersion) : minorVersion
    readonly property int minorCellAge: mergeMode ? (minorVersion !== "" ? minorAge : patchAge) : minorAge
    readonly property string minorCellBump: mergeMode ? (minorVersion !== "" ? "minor" : "patch") : "minor"

    readonly property bool showWarn: currentAge >= 0 && App.oldAgeThresholdDays > 0
                                     && currentAge >= App.oldAgeThresholdDays

    function fmtAgeWarn(days) {
        var years = Math.floor(days / 365)
        var months = Math.floor((days - years * 365) / 30)
        var age
        if (years && months)
            age = years + " year" + (years !== 1 ? "s" : "") + " " + months + " month" + (months !== 1 ? "s" : "")
        else if (years)
            age = years + " year" + (years !== 1 ? "s" : "")
        else
            age = (months || 1) + " month" + ((months || 1) !== 1 ? "s" : "")
        return qsTr("Installed version is %1 old — consider updating").arg(age)
    }

    function paletteFor(map, key, fallback) {
        var v = map[key]
        return v !== undefined ? v : fallback
    }

    readonly property var groupColors: ({
        "dependencies": Theme.dark ? ({ bg: "#1e3a5f", fg: "#93c5fd" }) : ({ bg: "#dbeafe", fg: "#1d4ed8" }),
        "dependencyManagement": Theme.dark ? ({ bg: "#14532d", fg: "#86efac" }) : ({ bg: "#f0fdf4", fg: "#15803d" }),
        "plugins": Theme.dark ? ({ bg: "#451a03", fg: "#fcd34d" }) : ({ bg: "#fefce8", fg: "#92400e" }),
        "parent": Theme.dark ? ({ bg: "#2e1065", fg: "#c4b5fd" }) : ({ bg: "#ede9fe", fg: "#6d28d9" })
    })
    readonly property var typeColors: ({
        "property": Theme.dark ? ({ bg: "#1e3a5f", fg: "#93c5fd" }) : ({ bg: "#dbeafe", fg: "#1d4ed8" }),
        "exact": Theme.dark ? ({ bg: "#1e293b", fg: "#94a3b8" }) : ({ bg: "#f1f5f9", fg: "#475569" }),
        "snapshot": Theme.dark ? ({ bg: "#431407", fg: "#fdba74" }) : ({ bg: "#ffedd5", fg: "#c2410c" }),
        "range": Theme.dark ? ({ bg: "#164e63", fg: "#67e8f9" }) : ({ bg: "#cffafe", fg: "#0e7490" })
    })
    readonly property var grpColor: paletteFor(groupColors, group, Theme.dark ? ({ bg: "#1e293b", fg: "#94a3b8" }) : ({ bg: "#e5e7eb", fg: "#374151" }))
    readonly property var typColor: paletteFor(typeColors, constraintType, Theme.dark ? ({ bg: "#1e293b", fg: "#94a3b8" }) : ({ bg: "#f1f5f9", fg: "#475569" }))

    Rectangle {
        anchors.bottom: parent.bottom
        width: parent.width
        height: 1
        color: Theme.border
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.preferredWidth: row.wSelect
            Layout.fillHeight: true
            AppCheckBox {
                anchors.centerIn: parent
                checked: row.selected
                enabled: !Project.isFetching && row.selectable
                onToggled: Project.setSelected(row.rowId, !row.selected)
            }
        }

        Item {
            Layout.preferredWidth: row.wGroup
            Layout.fillHeight: true
            Badge {
                anchors.centerIn: parent
                label: row.groupLabel
                bgColor: row.grpColor.bg
                fgColor: row.grpColor.fg
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: 10
                anchors.rightMargin: 6
                spacing: 6

                Text {
                    Layout.fillWidth: true
                    text: row.name
                    font.family: Theme.monoFamily
                    font.pixelSize: 14
                    color: Theme.textTable
                    elide: Text.ElideRight
                }
                Text {
                    visible: row.propertyName !== ""
                    text: qsTr("via ${%1}").arg(row.propertyName)
                    font.pixelSize: 11
                    color: Theme.textMuted
                }
                LinkButton {
                    text: qsTr("Central ↗")
                    linkUrl: row.centralUrl
                }
                LinkButton {
                    visible: row.repoUrl !== ""
                    text: row.repoLabel
                    linkUrl: row.repoUrl
                }
            }
        }

        Item {
            Layout.preferredWidth: row.wCurrent
            Layout.fillHeight: true
            RowLayout {
                anchors.centerIn: parent
                spacing: 6

                Text {
                    text: row.currentVersion
                    font.family: Theme.monoFamily
                    font.pixelSize: 14
                    color: Theme.textTable
                }

                Rectangle {
                    visible: row.needsInstall
                    implicitHeight: 18
                    implicitWidth: pendingLabel.implicitWidth + 12
                    radius: 4
                    color: Theme.dark ? "#451a03" : "#fef3c7"
                    border.width: 1
                    border.color: Theme.dark ? "#b45309" : "#fcd34d"
                    Text {
                        id: pendingLabel
                        anchors.centerIn: parent
                        text: qsTr("pending")
                        font.pixelSize: 11
                        font.bold: true
                        color: Theme.dark ? "#fcd34d" : "#92400e"
                    }
                }

                Text {
                    id: warnIcon
                    visible: row.showWarn
                    text: "⚠"
                    font.pixelSize: 14
                    color: Theme.warn
                    readonly property string warnText: row.fmtAgeWarn(row.currentAge)
                    HoverHandler { id: warnHover }
                    AppToolTip {
                        visible: warnHover.hovered
                        text: warnIcon.warnText
                    }
                }
            }
        }

        Item {
            Layout.preferredWidth: row.wType
            Layout.fillHeight: true
            Badge {
                anchors.centerIn: parent
                label: row.constraintTypeLabel
                bgColor: row.typColor.bg
                fgColor: row.typColor.fg
            }
        }

        VersionCell {
            Layout.preferredWidth: row.wVer
            Layout.fillHeight: true
            visible: !row.mergeMode
            rowId: row.rowId
            version: row.patchVersion
            ageDays: row.patchAge
            bumpType: "patch"
            status: row.isLoading ? "loading" : (row.isError ? "error" : (row.patchVersion !== "" ? "ok" : "none"))
            errorMsg: row.errorMessage
        }

        VersionCell {
            Layout.preferredWidth: row.wVer
            Layout.fillHeight: true
            rowId: row.rowId
            version: row.minorCellVer
            ageDays: row.minorCellAge
            bumpType: row.minorCellBump
            status: row.isLoading ? "loading" : (row.isError ? "error" : (row.minorCellVer !== "" ? "ok" : "none"))
            errorMsg: row.errorMessage
        }

        VersionCell {
            Layout.preferredWidth: row.wVer
            Layout.fillHeight: true
            rowId: row.rowId
            version: row.majorVersion
            ageDays: row.majorAge
            bumpType: "major"
            rightInset: 18
            status: row.isLoading ? "loading" : (row.isError ? "error" : (row.majorVersion !== "" ? "ok" : "none"))
            errorMsg: row.errorMessage
        }
    }
}
