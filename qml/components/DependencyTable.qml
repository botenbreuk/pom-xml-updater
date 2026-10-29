import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App
import "../controls"

Rectangle {
    id: frame

    color: Theme.surface
    radius: 10
    border.width: 1
    border.color: Theme.border
    clip: true

    readonly property real wSelect: 52
    readonly property real wDepMin: 240
    readonly property var defaultWidths: ({ "group": 74, "current": 150, "type": 110,
                                            "patch": 150, "minor": 150, "major": 150 })
    // Set by dragging the header dividers, and saved; the Dependency column takes the rest.
    property var widths: Object.assign({}, frame.defaultWidths, App.columnWidthsInitial)
    readonly property bool mergeMode: App.mergePatchMinor

    // The widths as laid out. When the window is too narrow for the dragged widths to
    // leave Dependency wDepMin, the width dragged beyond each default is handed back
    // proportionally; it returns once there is room again.
    readonly property var fittedWidths: {
        const extra = (k) => Math.max(0, frame.widths[k] - frame.defaultWidths[k])
        const shown = Object.keys(frame.defaultWidths).filter((k) => k !== "patch" || !frame.mergeMode)
        const total = shown.reduce((sum, k) => sum + frame.widths[k], 0)
        const totalExtra = shown.reduce((sum, k) => sum + extra(k), 0)
        const shortBy = frame.wDepMin - (frame.width - frame.wSelect - total)
        const handBack = totalExtra > 0 ? Math.min(1, Math.max(0, shortBy) / totalExtra) : 0
        const fitted = {}
        for (const k in frame.defaultWidths)
            fitted[k] = Math.round(frame.widths[k] - extra(k) * handBack)
        return fitted
    }
    // A drag never squeezes the Dependency column below wDepMin.
    readonly property real spareWidth: Math.max(0, depHeader.width - frame.wDepMin)

    function resizeColumn(key, w) {
        frame.widths = Object.assign({}, frame.widths, { [key]: w })
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            implicitHeight: 38
            color: Theme.surfaceAlt
            radius: frame.radius

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
                    Layout.preferredWidth: frame.wSelect
                    Layout.fillHeight: true
                    AppCheckBox {
                        anchors.centerIn: parent
                        checked: Project.headerChecked
                        enabled: !Project.isFetching && Project.selectableCount > 0
                        onToggled: Project.toggleSelectAll(!Project.headerChecked)
                    }
                }
                HeaderLabel {
                    Layout.preferredWidth: frame.fittedWidths.group
                    text: qsTr("Group")
                    center: true
                    resizeEdge: "right"
                    spareWidth: frame.spareWidth
                    onResized: (w) => frame.resizeColumn("group", w)
                    onResizeFinished: App.setColumnWidths(frame.widths)
                }
                HeaderLabel {
                    id: depHeader
                    Layout.fillWidth: true
                    text: qsTr("Dependency")
                    leftInset: 10
                }
                HeaderLabel {
                    Layout.preferredWidth: frame.fittedWidths.current
                    text: qsTr("Current")
                    center: true
                    resizeEdge: "left"
                    spareWidth: frame.spareWidth
                    onResized: (w) => frame.resizeColumn("current", w)
                    onResizeFinished: App.setColumnWidths(frame.widths)
                }
                HeaderLabel {
                    Layout.preferredWidth: frame.fittedWidths.type
                    text: qsTr("Type")
                    center: true
                    resizeEdge: "left"
                    spareWidth: frame.spareWidth
                    onResized: (w) => frame.resizeColumn("type", w)
                    onResizeFinished: App.setColumnWidths(frame.widths)
                }
                HeaderLabel {
                    Layout.preferredWidth: frame.fittedWidths.patch
                    visible: !frame.mergeMode
                    text: qsTr("Patch ↑")
                    center: true
                    resizeEdge: "left"
                    spareWidth: frame.spareWidth
                    onResized: (w) => frame.resizeColumn("patch", w)
                    onResizeFinished: App.setColumnWidths(frame.widths)
                }
                HeaderLabel {
                    Layout.preferredWidth: frame.fittedWidths.minor
                    text: frame.mergeMode ? qsTr("Minor / Patch ↑") : qsTr("Minor ↑")
                    center: true
                    resizeEdge: "left"
                    spareWidth: frame.spareWidth
                    onResized: (w) => frame.resizeColumn("minor", w)
                    onResizeFinished: App.setColumnWidths(frame.widths)
                }
                HeaderLabel {
                    Layout.preferredWidth: frame.fittedWidths.major
                    text: qsTr("Major ↑")
                    center: true
                    resizeEdge: "left"
                    spareWidth: frame.spareWidth
                    onResized: (w) => frame.resizeColumn("major", w)
                    onResizeFinished: App.setColumnWidths(frame.widths)
                }
            }
        }

        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            reuseItems: true
            // Off-screen rows are otherwise pre-built in the background; a filter dropping one
            // mid-build makes Qt warn "DelegateModel::cancel: index out range" on the next reset.
            cacheBuffer: 0
            boundsBehavior: Flickable.StopAtBounds
            model: Project.dependencies

            ScrollBar.vertical: ThinScrollBar {}

            delegate: DependencyRow {
                width: ListView.view.width
                wSelect: frame.wSelect
                wGroup: frame.fittedWidths.group
                wCurrent: frame.fittedWidths.current
                wType: frame.fittedWidths.type
                wPatch: frame.fittedWidths.patch
                wMinor: frame.fittedWidths.minor
                wMajor: frame.fittedWidths.major
                mergeMode: frame.mergeMode
            }

            Text {
                anchors.centerIn: parent
                visible: listView.count === 0 && Project.depCount > 0
                text: qsTr("All dependencies are up to date")
                font.pixelSize: Theme.fontSize
                color: Theme.textSubtle
            }
        }
    }
}
