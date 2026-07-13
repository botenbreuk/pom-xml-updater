import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts
import App
import "../controls"
import "../components"

Item {
    id: settingsPage

    Layout.fillWidth: true
    Layout.fillHeight: true

    property int navIndex: 0
    signal clearCacheRequested()

    function syncFromSettings() {
        ageSpin.value = App.minAgeDays
        ttlSpin.value = App.cacheTtlHours
        oldSpin.value = App.oldVersionThreshold
        unitCombo.currentIndex = App.oldVersionUnit === "years" ? 1 : 0
        defaultToolCombo.currentIndex = Math.max(0, defaultToolCombo.values.indexOf(App.defaultBuildTool))
    }

    Component.onCompleted: syncFromSettings()

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 190
            Layout.fillHeight: true
            color: Theme.surfaceAlt

            Column {
                anchors.fill: parent
                anchors.margins: 12
                spacing: 2

                Repeater {
                    model: [qsTr("Theme"), qsTr("Version Age Filter"), qsTr("Old Version Warning"),
                            qsTr("Version Cache"), qsTr("Display"), qsTr("Build Tools"), qsTr("About")]

                    Rectangle {
                        required property int index
                        required property string modelData
                        width: parent.width
                        height: 34
                        radius: 6
                        readonly property bool active: settingsPage.navIndex === index
                        color: active ? Theme.accentSoftBg
                                      : (navMouse.containsMouse ? Theme.surfaceMuted : "transparent")

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            anchors.left: parent.left
                            anchors.leftMargin: 12
                            text: parent.modelData
                            color: parent.active ? Theme.accentHover : Theme.textMuted
                            font.pixelSize: 14
                            font.bold: parent.active
                        }

                        MouseArea {
                            id: navMouse
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: settingsPage.navIndex = parent.index
                        }
                    }
                }
            }
        }

        Rectangle { Layout.preferredWidth: 1; Layout.fillHeight: true; color: Theme.border }

        StackLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            currentIndex: settingsPage.navIndex

            // ── Theme ───────────────────────────────────────────────────────
            ScrollView {
                contentWidth: availableWidth
                ScrollBar.vertical: ThinScrollBar {}
                ColumnLayout {
                    width: parent.width
                    Item { Layout.preferredHeight: 28 }

                    Text { text: qsTr("Theme"); color: Theme.textHeading; font.pixelSize: 20; font.bold: true; Layout.leftMargin: 32 }
                    Text {
                        text: qsTr("System default follows your OS light/dark preference.")
                        color: Theme.textMuted; font.pixelSize: 14; wrapMode: Text.WordWrap
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true
                    }

                    Flow {
                        Layout.fillWidth: true
                        Layout.leftMargin: 32
                        Layout.rightMargin: 32
                        Layout.topMargin: 8
                        spacing: 12
                        ThemeCard { value: "system"; label: qsTr("System default"); selected: App.theme === "system"; onPicked: (v) => App.setTheme(v) }
                        ThemeCard { value: "light"; label: qsTr("Light"); selected: App.theme === "light"; onPicked: (v) => App.setTheme(v) }
                        ThemeCard { value: "dark"; label: qsTr("Dark"); selected: App.theme === "dark"; onPicked: (v) => App.setTheme(v) }
                    }
                    Item { Layout.fillHeight: true; Layout.preferredHeight: 28 }
                }
            }

            // ── Version Age Filter ──────────────────────────────────────────
            ScrollView {
                contentWidth: availableWidth
                ScrollBar.vertical: ThinScrollBar {}
                ColumnLayout {
                    width: parent.width
                    Item { Layout.preferredHeight: 28 }
                    Text { text: qsTr("Version Age Filter"); color: Theme.textHeading; font.pixelSize: 20; font.bold: true; Layout.leftMargin: 32 }
                    Text {
                        text: qsTr("Only show dependency versions published at least this many days ago. Helps avoid freshly released artifacts that might still be pulled or superseded. Set to 0 to disable the filter.")
                        color: Theme.textMuted; font.pixelSize: 14; wrapMode: Text.WordWrap
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true
                    }
                    RowLayout {
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true; Layout.topMargin: 4
                        Text { text: qsTr("Minimum age:"); color: Theme.textBody; font.pixelSize: Theme.fontSize }
                        Item { Layout.fillWidth: true }
                        AppSpinBox { id: ageSpin; from: 0; to: 365; suffix: qsTr(" days"); specialText: qsTr("No filter (0 days)") }
                    }
                    RowLayout {
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true; Layout.topMargin: 4
                        Item { Layout.fillWidth: true }
                        AppButton { variant: "primary"; text: qsTr("Save"); Layout.minimumWidth: 90; onClicked: App.saveAgeFilter(ageSpin.value) }
                    }
                    Item { Layout.fillHeight: true; Layout.preferredHeight: 28 }
                }
            }

            // ── Old Version Warning ─────────────────────────────────────────
            ScrollView {
                contentWidth: availableWidth
                ScrollBar.vertical: ThinScrollBar {}
                ColumnLayout {
                    width: parent.width
                    Item { Layout.preferredHeight: 28 }
                    Text { text: qsTr("Old Version Warning"); color: Theme.textHeading; font.pixelSize: 20; font.bold: true; Layout.leftMargin: 32 }
                    Text {
                        text: qsTr("Show a ⚠ warning next to the installed version when it has not been updated for longer than this threshold. Set to 0 to disable.")
                        color: Theme.textMuted; font.pixelSize: 14; wrapMode: Text.WordWrap
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true
                    }
                    RowLayout {
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true; Layout.topMargin: 4
                        Text { text: qsTr("Warn after:"); color: Theme.textBody; font.pixelSize: Theme.fontSize }
                        Item { Layout.fillWidth: true }
                        AppSpinBox { id: oldSpin; from: 0; to: 99; boxWidth: 80; specialText: qsTr("Disabled") }
                        AppComboBox {
                            id: unitCombo
                            Layout.preferredWidth: 100
                            model: [qsTr("months"), qsTr("years")]
                            values: ["months", "years"]
                        }
                    }
                    RowLayout {
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true; Layout.topMargin: 4
                        Item { Layout.fillWidth: true }
                        AppButton { variant: "primary"; text: qsTr("Save"); Layout.minimumWidth: 90; onClicked: App.saveOldVersion(oldSpin.value, unitCombo.values[unitCombo.currentIndex]) }
                    }
                    Item { Layout.fillHeight: true; Layout.preferredHeight: 28 }
                }
            }

            // ── Version Cache ───────────────────────────────────────────────
            ScrollView {
                contentWidth: availableWidth
                ScrollBar.vertical: ThinScrollBar {}
                ColumnLayout {
                    width: parent.width
                    Item { Layout.preferredHeight: 28 }
                    Text { text: qsTr("Version Cache"); color: Theme.textHeading; font.pixelSize: 20; font.bold: true; Layout.leftMargin: 32 }
                    Text {
                        text: qsTr("Cached results make subsequent opens instant. Use ↺ Refresh to always get the latest versions regardless of this setting.")
                        color: Theme.textMuted; font.pixelSize: 14; wrapMode: Text.WordWrap
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true
                    }
                    Text {
                        text: { App.cacheRevision; return App.cacheInfoFor(ttlSpin.value) }
                        color: Theme.textBody; font.pixelSize: 13; Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true; wrapMode: Text.WordWrap
                    }
                    RowLayout {
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true; Layout.topMargin: 4
                        Text { text: qsTr("Cache TTL:"); color: Theme.textBody; font.pixelSize: Theme.fontSize }
                        Item { Layout.fillWidth: true }
                        AppSpinBox {
                            id: ttlSpin; from: 0; to: 672; specialText: qsTr("Disabled")
                            textFromValue: function(v) {
                                if (v % 168 === 0) { var w = v / 168; return w + (w === 1 ? qsTr(" week") : qsTr(" weeks")) }
                                if (v % 24  === 0) { var d = v / 24;  return d + (d === 1 ? qsTr(" day")  : qsTr(" days"))  }
                                return v + qsTr(" hours")
                            }
                            computeNext: function(v) { return v >= 168 ? v + 168 : v >= 24 ? v + 24 : v + 1 }
                            computePrev: function(v) { return v > 168  ? v - 168 : v > 24  ? v - 24 : v - 1 }
                        }
                    }
                    RowLayout {
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true; Layout.topMargin: 4
                        Item { Layout.fillWidth: true }
                        AppButton { variant: "primary"; text: qsTr("Save"); Layout.minimumWidth: 90; onClicked: App.saveCacheTtl(ttlSpin.value) }
                    }
                    Rectangle { Layout.fillWidth: true; Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.topMargin: 8; implicitHeight: 1; color: Theme.border }
                    Text { text: qsTr("Clear Cache"); color: Theme.textBody; font.pixelSize: 16; font.bold: true; Layout.leftMargin: 32 }
                    Text {
                        text: qsTr("Delete all locally stored version data. The next time you open a project all dependency information will be re-fetched fresh from Maven Central.")
                        color: Theme.textMuted; font.pixelSize: 14; wrapMode: Text.WordWrap
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true
                    }
                    AppButton {
                        variant: "danger-ghost"
                        text: qsTr("Clear Cache Now")
                        Layout.leftMargin: 32
                        onClicked: settingsPage.clearCacheRequested()
                    }
                    Item { Layout.fillHeight: true; Layout.preferredHeight: 28 }
                }
            }

            // ── Display ─────────────────────────────────────────────────────
            ScrollView {
                contentWidth: availableWidth
                ScrollBar.vertical: ThinScrollBar {}
                ColumnLayout {
                    width: parent.width
                    Item { Layout.preferredHeight: 28 }
                    Text { text: qsTr("Display"); color: Theme.textHeading; font.pixelSize: 20; font.bold: true; Layout.leftMargin: 32 }
                    Text {
                        text: qsTr("Customize how version updates are shown in the table.")
                        color: Theme.textMuted; font.pixelSize: 14; wrapMode: Text.WordWrap
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true
                    }
                    Rectangle { Layout.fillWidth: true; Layout.leftMargin: 32; Layout.rightMargin: 32; implicitHeight: 1; color: Theme.border }
                    Text { text: qsTr("Merge Patch and Minor"); color: Theme.textBody; font.pixelSize: 16; font.bold: true; Layout.leftMargin: 32 }
                    Text {
                        text: qsTr("When enabled, the Patch and Minor columns are merged into one. The highest available update between the two is shown.")
                        color: Theme.textMuted; font.pixelSize: 14; wrapMode: Text.WordWrap
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true
                    }
                    AppCheckBox {
                        Layout.leftMargin: 32
                        label: qsTr("Merge Patch and Minor updates")
                        checked: App.mergePatchMinor
                        onToggled: App.setMergePatchMinor(!App.mergePatchMinor)
                    }
                    Item { Layout.fillHeight: true; Layout.preferredHeight: 28 }
                }
            }

            // ── Build Tools ─────────────────────────────────────────────────
            ScrollView {
                contentWidth: availableWidth
                ScrollBar.vertical: ThinScrollBar {}
                ColumnLayout {
                    width: parent.width
                    Item { Layout.preferredHeight: 28 }
                    Text { text: qsTr("Build Tools"); color: Theme.textHeading; font.pixelSize: 20; font.bold: true; Layout.leftMargin: 32 }
                    Text {
                        text: qsTr("The build tool is detected from each project: a Maven Wrapper script (mvnw) wins when present. You can pin a folder to a specific tool from the 🪶 badge in the toolbar.")
                        color: Theme.textMuted; font.pixelSize: 14; wrapMode: Text.WordWrap
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true
                    }

                    Rectangle { Layout.fillWidth: true; Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.topMargin: 8; implicitHeight: 1; color: Theme.border }

                    Text { text: qsTr("Default"); color: Theme.textBody; font.pixelSize: 16; font.bold: true; Layout.leftMargin: 32 }
                    Text {
                        text: qsTr("Used when a project has no Maven Wrapper and no pinned folder override.")
                        color: Theme.textMuted; font.pixelSize: 14; wrapMode: Text.WordWrap
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true
                    }
                    RowLayout {
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true; Layout.topMargin: 4
                        Text { text: qsTr("Default build tool:"); color: Theme.textBody; font.pixelSize: Theme.fontSize }
                        Item { Layout.fillWidth: true }
                        AppComboBox {
                            id: defaultToolCombo
                            Layout.preferredWidth: 160
                            model: [qsTr("Maven"), qsTr("Maven Wrapper"), qsTr("Maven Daemon")]
                            values: ["mvn", "mvnw", "mvnd"]
                            onValuePicked: (value) => App.setDefaultBuildTool(value)
                        }
                    }

                    Rectangle { Layout.fillWidth: true; Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.topMargin: 8; implicitHeight: 1; color: Theme.border }

                    Text { text: qsTr("Per-folder overrides"); color: Theme.textBody; font.pixelSize: 16; font.bold: true; Layout.leftMargin: 32 }
                    Text {
                        text: qsTr("Folders you've pinned to a specific build tool. Remove one to fall back to detection.")
                        color: Theme.textMuted; font.pixelSize: 14; wrapMode: Text.WordWrap
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.fillWidth: true
                    }

                    Text {
                        visible: App.buildToolOverrides.length === 0
                        text: qsTr("No per-folder overrides yet.")
                        color: Theme.textSubtle; font.pixelSize: 14
                        Layout.leftMargin: 32; Layout.topMargin: 4
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.leftMargin: 32; Layout.rightMargin: 32; Layout.topMargin: 4
                        spacing: 6

                        Repeater {
                            model: App.buildToolOverrides
                            delegate: Rectangle {
                                id: ovRow
                                required property var modelData
                                Layout.fillWidth: true
                                implicitHeight: 44
                                radius: 8
                                color: Theme.surfaceAlt
                                border.width: 1
                                border.color: Theme.border

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 12
                                    anchors.rightMargin: 8
                                    spacing: 10

                                    Rectangle {
                                        implicitWidth: nameLabel.implicitWidth + 16
                                        implicitHeight: 22
                                        radius: 5
                                        color: Theme.surfaceMuted
                                        border.width: 1
                                        border.color: Theme.border
                                        Text {
                                            id: nameLabel
                                            anchors.centerIn: parent
                                            text: ovRow.modelData.name
                                            font.pixelSize: 12
                                            font.bold: true
                                            color: Theme.textBody
                                        }
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: ovRow.modelData.path
                                        font.pixelSize: 13
                                        font.family: Theme.monoFamily
                                        color: Theme.textMuted
                                        elide: Text.ElideMiddle
                                    }

                                    AppButton {
                                        variant: "danger-ghost"
                                        text: qsTr("Remove")
                                        topPadding: 6; bottomPadding: 6; leftPadding: 12; rightPadding: 12
                                        onClicked: App.removeBuildToolOverride(ovRow.modelData.path)
                                    }
                                }
                            }
                        }
                    }

                    Item { Layout.fillHeight: true; Layout.preferredHeight: 28 }
                }
            }

            // ── About ───────────────────────────────────────────────────────
            ScrollView {
                contentWidth: availableWidth
                ScrollBar.vertical: ThinScrollBar {}
                ColumnLayout {
                    width: parent.width
                    Item { Layout.preferredHeight: 28 }
                    Text { text: qsTr("About"); color: Theme.textHeading; font.pixelSize: 20; font.bold: true; Layout.leftMargin: 32 }
                    Rectangle { Layout.fillWidth: true; Layout.leftMargin: 32; Layout.rightMargin: 32; implicitHeight: 1; color: Theme.border }
                    Text { text: qsTr("Pom.xml Updater"); color: Theme.textBody; font.pixelSize: 16; font.bold: true; Layout.leftMargin: 32 }
                    Text { text: qsTr("Version %1").arg(App.appVersion); color: Theme.textMuted; font.pixelSize: 14; Layout.leftMargin: 32 }
                    Item { Layout.fillHeight: true; Layout.preferredHeight: 28 }
                }
            }
        }
    }
}
