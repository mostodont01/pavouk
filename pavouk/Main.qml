import QtQuick
import QtQuick.Window

Window {
    id: win
    required property var bracket

    width: 1060
    height: 640
    visible: true
    title: "Pavouk"
    color: "#ffffff"

    // ---- layout constants (in design units, scaled to the window) ----
    readonly property int colW: 230
    readonly property int boxW: 180
    readonly property int boxH: 40
    readonly property int top: 70
    readonly property int left: 30
    readonly property int nTeams: Math.pow(2, bracket.rounds)
    readonly property real designW: left * 2 + bracket.rounds * colW + boxW
    readonly property real designH: slotTop(0, nTeams - 1) + boxH + 50

    function slotTop(r, i) {        // top edge of slot i in round r
        if (r === 0)
            return top + i * 52 + Math.floor(i / 2) * 30
        return (slotTop(r - 1, 2 * i) + slotTop(r - 1, 2 * i + 1)) / 2
    }
    function colX(r) { return left + r * colW }

    Shortcut { sequence: "F11"; onActivated: win.visibility = win.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen }
    Shortcut { sequence: "Esc"; onActivated: win.visibility = Window.Windowed }

    Item {
        id: board
        objectName: "board"
        width: win.designW
        height: win.designH
        anchors.centerIn: parent
        scale: Math.min(win.width / width, win.height / height)

        // connectors
        Canvas {
            id: lines
            anchors.fill: parent
            property int rev: win.bracket.revision
            onRevChanged: requestPaint()
            onPaint: {
                const ctx = getContext("2d")
                ctx.reset()
                ctx.lineWidth = 2
                for (let r = 0; r < win.bracket.rounds; r++) {
                    const n = Math.pow(2, win.bracket.rounds - r)
                    for (let m = 0; m < n / 2; m++) {
                        const w = win.bracket.winner(r, m)
                        const xe = win.colX(r) + win.boxW
                        const xm = xe + (win.colW - win.boxW) / 2
                        const ya = win.slotTop(r, 2 * m) + win.boxH / 2
                        const yb = win.slotTop(r, 2 * m + 1) + win.boxH / 2
                        const ym = (ya + yb) / 2
                        const seg = (pts, on) => {
                            ctx.strokeStyle = on ? "#16a34a" : "#b8c0ca"
                            ctx.lineWidth = on ? 3 : 2
                            ctx.beginPath()
                            ctx.moveTo(pts[0][0], pts[0][1])
                            for (let k = 1; k < pts.length; k++) ctx.lineTo(pts[k][0], pts[k][1])
                            ctx.stroke()
                        }
                        seg([[xe, ya], [xm, ya], [xm, ym]], false)
                        seg([[xe, yb], [xm, yb], [xm, ym]], false)
                        seg([[xm, ym], [win.colX(r + 1), ym]], false)
                        if (w >= 0) {
                            const y = w === 0 ? ya : yb
                            seg([[xe, y], [xm, y], [xm, ym], [win.colX(r + 1), ym]], true)
                        }
                    }
                }
            }
        }

        // round headers + slots
        Repeater {
            model: win.bracket.rounds + 1
            delegate: Item {
                id: col
                required property int index
                readonly property int r: index
                readonly property bool isChampion: r === win.bracket.rounds
                readonly property var names: { win.bracket.revision; return win.bracket.slots(r) }

                Text {
                    x: win.colX(col.r); y: 22; width: win.boxW
                    horizontalAlignment: Text.AlignHCenter
                    text: win.bracket.roundName(col.r).toUpperCase()
                    font.pixelSize: 15; font.bold: true; font.letterSpacing: 1
                    color: "#52606d"
                }

                Repeater {
                    model: col.names.length
                    delegate: Rectangle {
                        id: slot
                        required property int index
                        objectName: "slot_" + col.r + "_" + index
                        readonly property string name: col.names[index]
                        readonly property int match: Math.floor(index / 2)
                        readonly property int side: index % 2
                        readonly property int result: { win.bracket.revision; return win.bracket.winner(col.r, match) }
                        readonly property bool won: result === side
                        readonly property bool lost: result >= 0 && !won
                        readonly property bool clickable: !col.isChampion && name !== ""
                            && col.names[2 * match] !== "" && col.names[2 * match + 1] !== ""

                        x: win.colX(col.r); y: win.slotTop(col.r, index)
                        width: win.boxW; height: win.boxH; radius: 7
                        color: col.isChampion ? (name ? "#fff4c2" : "#fffbea")
                             : won ? "#e8f8ee"
                             : name === "" ? "#f5f7fa"
                             : mouse.containsMouse && clickable ? "#eef4ff" : "#ffffff"
                        border.width: col.isChampion || won ? 2.5 : 1.5
                        border.color: col.isChampion ? "#d4a017"
                                    : won ? "#16a34a"
                                    : mouse.containsMouse && clickable ? "#3b82f6" : "#b8c0ca"
                        opacity: lost ? 0.45 : 1

                        Text {
                            anchors.verticalCenter: parent.verticalCenter
                            x: 12; width: parent.width - 24
                            elide: Text.ElideRight
                            text: slot.name !== "" ? (col.isChampion ? "🏆 " + slot.name : slot.name)
                                : col.isChampion ? "🏆 ?" : "?"
                            font.pixelSize: 16
                            font.bold: slot.name !== ""
                            font.strikeout: slot.lost
                            color: col.isChampion ? "#7a5b00" : slot.name === "" ? "#9aa5b1" : "#1f2933"
                        }

                        MouseArea {
                            id: mouse
                            anchors.fill: parent
                            hoverEnabled: true
                            enabled: slot.clickable
                            cursorShape: slot.clickable ? Qt.PointingHandCursor : Qt.ArrowCursor
                            onClicked: win.bracket.pick(col.r, slot.match, slot.side)
                        }
                    }
                }
            }
        }

        // footer: hint + reset
        Text {
            x: win.left; y: win.designH - 34
            text: "Klikni na tým, který vyhrál. Další klik výsledek zruší.  ·  F11 celá obrazovka"
            font.pixelSize: 13; color: "#7b8794"
        }

        Rectangle {
            id: resetBtn
            objectName: "resetButton"
            property bool armed: false
            width: 150; height: 32; radius: 6
            x: win.designW - win.left - width; y: win.designH - 42
            color: armed ? "#dc2626" : resetMouse.containsMouse ? "#f1f5f9" : "#ffffff"
            border.color: armed ? "#dc2626" : "#b8c0ca"
            Text {
                anchors.centerIn: parent
                text: resetBtn.armed ? "Opravdu smazat?" : "Nový turnaj"
                font.pixelSize: 14; font.bold: resetBtn.armed
                color: resetBtn.armed ? "#ffffff" : "#1f2933"
            }
            Timer { id: disarm; interval: 3000; onTriggered: resetBtn.armed = false }
            MouseArea {
                id: resetMouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: {
                    if (resetBtn.armed) { win.bracket.reset(); resetBtn.armed = false; disarm.stop() }
                    else { resetBtn.armed = true; disarm.restart() }
                }
            }
        }
    }
}
