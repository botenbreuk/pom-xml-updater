import QtQuick

// Static schematic of the app, used by the theme cards. The "system" variant
// shows the light palette on the left and dark on the right, split diagonally
// (ported from the original QPainter preview).
Canvas {
    id: preview

    property string variant: "light"

    implicitWidth: 190
    implicitHeight: 110

    readonly property var lightPalette: ({
        bg: "#f8fafc", toolbar: "#ffffff", border: "#e2e8f0",
        rowAlt: "#f1f5f9", muted: "#cbd5e1", accent: "#3b82f6"
    })
    readonly property var darkPalette: ({
        bg: "#0f172a", toolbar: "#1e293b", border: "#334155",
        rowAlt: "#1e293b", muted: "#334155", accent: "#3b82f6"
    })

    onVariantChanged: requestPaint()

    function roundRectPath(ctx, x, y, w, h, r) {
        ctx.beginPath()
        ctx.moveTo(x + r, y)
        ctx.arcTo(x + w, y, x + w, y + h, r)
        ctx.arcTo(x + w, y + h, x, y + h, r)
        ctx.arcTo(x, y + h, x, y, r)
        ctx.arcTo(x, y, x + w, y, r)
        ctx.closePath()
    }

    function paintUI(ctx, c, w, h) {
        ctx.fillStyle = c.bg
        ctx.fillRect(0, 0, w, h)

        var th = Math.max(12, h / 5)
        ctx.fillStyle = c.toolbar
        ctx.fillRect(0, 0, w, th)
        ctx.fillStyle = c.border
        ctx.fillRect(0, th, w, Math.max(1, h / 80))

        var btnH = Math.max(3, th / 4)
        var btnW = Math.max(5, th / 2)
        var gap = btnW + Math.max(4, th / 5)
        var btnY = (th - btnH) / 2
        ctx.fillStyle = c.muted
        for (var i = 0; i < 3; i++)
            ctx.fillRect(4 + i * gap, btnY, btnW, btnH)

        var accW = Math.max(8, th * 2 / 3)
        var accH = Math.max(4, th / 3)
        ctx.fillStyle = c.accent
        ctx.fillRect(w - accW - 4, (th - accH) / 2, accW, accH)

        var sb = Math.max(8, h / 8)
        var cy = th + 2
        var rowH = Math.max(6, (h - th - 2 - sb) / 3)
        var barH = Math.max(2, rowH / 5)
        for (i = 0; i < 3; i++) {
            ctx.fillStyle = (i % 2) ? c.rowAlt : c.bg
            ctx.fillRect(0, cy, w, rowH)
            ctx.fillStyle = c.muted
            ctx.fillRect(4, cy + (rowH - barH) / 2, w * 0.44, barH)
            ctx.fillRect(w - w * 0.22, cy + (rowH - barH) / 2, w * 0.17, barH)
            cy += rowH
        }

        ctx.fillStyle = c.toolbar
        ctx.fillRect(0, h - sb, w, sb)
        ctx.fillStyle = c.muted
        ctx.fillRect(4, h - sb + (sb - barH) / 2, w * 0.32, barH)
    }

    onPaint: {
        var ctx = getContext("2d")
        ctx.reset()
        ctx.save()
        roundRectPath(ctx, 0, 0, width, height, 6)
        ctx.clip()

        if (variant === "dark") {
            paintUI(ctx, darkPalette, width, height)
        } else if (variant === "light") {
            paintUI(ctx, lightPalette, width, height)
        } else {
            paintUI(ctx, lightPalette, width, height)
            ctx.save()
            ctx.beginPath()
            ctx.moveTo(width * 0.42, 0)
            ctx.lineTo(width, 0)
            ctx.lineTo(width, height)
            ctx.lineTo(width * 0.58, height)
            ctx.closePath()
            ctx.clip()
            paintUI(ctx, darkPalette, width, height)
            ctx.restore()

            ctx.strokeStyle = "#64748b"
            ctx.lineWidth = 1
            ctx.beginPath()
            ctx.moveTo(width * 0.42, 0)
            ctx.lineTo(width * 0.58, height)
            ctx.stroke()
        }
        ctx.restore()
    }
}
