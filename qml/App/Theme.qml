pragma Singleton
import QtQuick

QtObject {
    id: theme

    // Synced to AppController.dark by Main.qml so every component reacts to it.
    property bool dark: false

    readonly property int fontSize: 15
    readonly property string monoFamily: Qt.platform.os === "osx" ? "Menlo"
                                        : Qt.platform.os === "windows" ? "Consolas" : "monospace"

    // ── surfaces ────────────────────────────────────────────────────────────
    readonly property color window:       dark ? "#0f172a" : "#f8fafc"
    readonly property color surface:       dark ? "#1e293b" : "#ffffff"
    readonly property color surfaceAlt:    dark ? "#172032" : "#f8fafc"
    readonly property color surfaceMuted:  dark ? "#1e293b" : "#f1f5f9"
    readonly property color border:        dark ? "#334155" : "#e2e8f0"
    readonly property color borderStrong:  dark ? "#475569" : "#cbd5e1"

    // ── toolbar / status bar ────────────────────────────────────────────────
    readonly property color toolbarBg:      dark ? "#1e293b" : "#ffffff"
    readonly property color toolbarHover:   dark ? "#334155" : "#f1f5f9"
    readonly property color toolbarPressed: dark ? "#475569" : "#e2e8f0"
    readonly property color statusBg:       dark ? "#0f172a" : "#f8fafc"
    readonly property color statusText:     dark ? "#94a3b8" : "#475569"

    // ── text ────────────────────────────────────────────────────────────────
    readonly property color textHeading: dark ? "#f1f5f9" : "#0f172a"
    readonly property color textBody:    dark ? "#cbd5e1" : "#334155"
    readonly property color textTable:   dark ? "#e2e8f0" : "#1e293b"
    readonly property color textMuted:   dark ? "#94a3b8" : "#64748b"
    readonly property color textSubtle:  dark ? "#94a3b8" : "#64748b"
    readonly property color textFaint:   dark ? "#475569" : "#94a3b8"

    // ── accent (blue) ─────────────────────────────────────────────────────────
    readonly property color accent:         "#3b82f6"
    readonly property color accentHover:    dark ? "#2563eb" : "#2563eb"
    readonly property color accentPressed:  "#1d4ed8"
    readonly property color accentDisabled: dark ? "#1e3a8a" : "#bfdbfe"
    readonly property color accentSoftBg:   dark ? "#1e3a5f" : "#eff6ff"
    readonly property color textOnAccent:   "#ffffff"

    // ── purple (Update All) ─────────────────────────────────────────────────
    readonly property color purple:         "#8b5cf6"
    readonly property color purpleHover:    "#7c3aed"
    readonly property color purplePressed:  "#6d28d9"
    readonly property color purpleDisabled: dark ? "#3b0764" : "#ddd6fe"

    // ── status colours ──────────────────────────────────────────────────────
    readonly property color danger:        "#ef4444"
    readonly property color dangerHover:    "#dc2626"
    readonly property color dangerPressed:  "#b91c1c"
    readonly property color warn:          dark ? "#f59e0b" : "#d97706"
    readonly property color success:       dark ? "#4ade80" : "#15803d"
}
