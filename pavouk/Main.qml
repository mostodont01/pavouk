import QtQuick
import QtQuick.Window
import QtQuick.Shapes
import QtQuick.Controls.Basic

Window {
    id: win
    required property var bracket

    width: 1100
    height: 700
    visible: true
    title: bracket.started && bracket.champion !== "" ? "Pavouk · vítěz: " + bracket.champion : "Pavouk"
    color: "#ffffff"

    Shortcut { sequence: "F11"; onActivated: win.visibility = win.visibility === Window.FullScreen ? Window.Windowed : Window.FullScreen }
    Shortcut { sequence: "Esc"; onActivated: win.visibility = Window.Windowed }

    // ---------------------------------------------------------- intro ----
    Item {
        id: intro
        objectName: "intro"
        anchors.fill: parent
        visible: !win.bracket.started

        readonly property string err: { win.bracket.revision; return win.bracket.check(names.text) }
        readonly property int n: { win.bracket.revision; return win.bracket.count(names.text) }
        readonly property int size: { let s = 1; while (s < n) s *= 2; return s }
        readonly property int rounds: Math.round(Math.log(size) / Math.LN2)

        function go() {
            const e = win.bracket.start(names.text)
            if (e !== "") errText.text = e
        }

        Column {
            anchors.centerIn: parent
            width: Math.min(520, parent.width - 40)
            spacing: 14

            Text { text: "Pavouk"; font.pixelSize: 40; font.bold: true; color: "#1f2933" }
            Text {
                width: parent.width; wrapMode: Text.Wrap
                text: "Napiš týmy, každý na nový řádek (" + 2 + "–" + win.bracket.maxTeams + "). Rozlosují se náhodně do pavouka; když jich není 2, 4, 8, 16…, někteří dostanou volno."
                font.pixelSize: 15; color: "#52606d"
            }

            Rectangle {
                width: parent.width
                height: Math.min(360, Math.max(220, win.height - 300))
                radius: 8
                border.color: names.activeFocus ? "#3b82f6" : "#b8c0ca"
                border.width: names.activeFocus ? 2 : 1.5
                ScrollView {
                    anchors.fill: parent
                    anchors.margins: 4
                    TextArea {
                        id: names
                        objectName: "namesInput"
                        text: win.bracket.lastNames
                        placeholderText: "Tým 1\nTým 2\nTým 3\n…"
                        font.pixelSize: 17
                        color: "#1f2933"
                        wrapMode: TextArea.NoWrap
                        background: null
                        focus: true
                        Keys.onPressed: (e) => {
                            if ((e.key === Qt.Key_Return || e.key === Qt.Key_Enter) && (e.modifiers & Qt.ControlModifier)) {
                                intro.go(); e.accepted = true
                            }
                        }
                        onTextChanged: errText.text = ""
                    }
                }
            }

            // hard error from a start attempt (red); otherwise live info / hint
            QtObject { id: errText; property string text: "" }
            Text {
                objectName: "statusText"
                width: parent.width; wrapMode: Text.Wrap
                font.pixelSize: 14
                readonly property string info: intro.n + " " + (intro.n === 1 ? "tým" : intro.n < 5 && intro.n > 0 ? "týmy" : "týmů")
                    + " · " + intro.rounds + " " + (intro.rounds === 1 ? "kolo" : intro.rounds < 5 ? "kola" : "kol")
                    + (intro.size > intro.n ? " · volno: " + (intro.size - intro.n) : "")
                text: errText.text !== "" ? errText.text : intro.err !== "" ? intro.err : info
                color: errText.text !== "" ? "#dc2626" : intro.err !== "" ? "#9aa5b1" : "#52606d"
            }

            Row {
                spacing: 10
                AppButton {
                    objectName: "startButton"
                    text: "Zamíchat a začít"
                    primary: true
                    enabled: intro.err === ""
                    onClicked: intro.go()
                }
                AppButton {
                    objectName: "resumeButton"
                    visible: win.bracket.canResume
                    text: "Zpět k rozehranému"
                    onClicked: win.bracket.resume()
                }
            }
            Text { text: "Ctrl+Enter = začít"; font.pixelSize: 12; color: "#9aa5b1" }
        }
    }

    // -------------------------------------------------------- bracket ----
    Item {
        id: page
        objectName: "bracketPage"
        anchors.fill: parent
        visible: win.bracket.started

        readonly property int rounds: win.bracket.rounds
        readonly property int nSlots: rounds > 0 ? Math.pow(2, rounds) : 0
        readonly property bool compact: nSlots > 16
        readonly property int colW: compact ? 210 : 230
        readonly property int boxW: compact ? 168 : 180
        readonly property int boxH: compact ? 32 : 40
        readonly property int pitch: boxH + (compact ? 8 : 12)
        readonly property int pairGap: compact ? 14 : 30
        readonly property int padTop: 56
        readonly property int padLeft: 30
        readonly property real designW: padLeft * 2 + rounds * colW + boxW
        readonly property real designH: nSlots > 0 ? slotTop(0, nSlots - 1) + boxH + 30 : 100
        readonly property real fitZoom: Math.min(flick.width / designW, flick.height / designH, 1.6)
        // auto: whole bracket if it fits, otherwise at least fit the width (scroll down)
        readonly property real autoZoom: flick.width > 0 && flick.height > 0
            ? Math.max(fitZoom, Math.min(1, flick.width / designW)) : 1
        property real manualZoom: 1
        property bool autoFit: true
        readonly property real zoom: autoFit ? autoZoom : manualZoom

        function slotTop(r, i) {
            if (r === 0) return padTop + i * pitch + Math.floor(i / 2) * pairGap
            return (slotTop(r - 1, 2 * i) + slotTop(r - 1, 2 * i + 1)) / 2
        }
        function colX(r) { return padLeft + r * colW }
        function fit() { autoFit = true }
        function zoomBy(f) { manualZoom = Math.max(0.2, Math.min(3, zoom * f)); autoFit = false }

        // toolbar
        Rectangle {
            id: bar
            width: parent.width; height: 52
            color: "#f8fafc"
            border.color: "#e4e7eb"
            Row {
                anchors.left: parent.left; anchors.leftMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                AppButton { objectName: "backButton"; text: "← Týmy"; onClicked: win.bracket.backToIntro() }
                AppButton {
                    id: redrawBtn
                    objectName: "redrawButton"
                    text: armed ? "Opravdu nový los?" : "Nový los"
                    property bool armed: false
                    danger: armed
                    Timer { id: redrawDisarm; interval: 3000; onTriggered: redrawBtn.armed = false }
                    onClicked: {
                        if (armed) { armed = false; win.bracket.start(win.bracket.lastNames) }
                        else { armed = true; redrawDisarm.restart() }
                    }
                }
                AppButton {
                    id: resetBtn
                    objectName: "resetButton"
                    text: armed ? "Opravdu smazat?" : "Smazat výsledky"
                    property bool armed: false
                    danger: armed
                    Timer { id: disarm; interval: 3000; onTriggered: resetBtn.armed = false }
                    onClicked: {
                        if (armed) { win.bracket.reset(); armed = false; disarm.stop() }
                        else { armed = true; disarm.restart() }
                    }
                }
            }
            Row {
                anchors.right: parent.right; anchors.rightMargin: 14
                anchors.verticalCenter: parent.verticalCenter
                spacing: 8
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Klikni na vítěze · Ctrl+kolečko zoom · F11 celá obrazovka"
                    font.pixelSize: 12; color: "#7b8794"
                    visible: win.width > 900
                }
                AppButton { text: "−"; width: 36; onClicked: page.zoomBy(1 / 1.2) }
                AppButton { text: Math.round(page.zoom * 100) + " %"; width: 70; onClicked: page.fit() }
                AppButton { text: "+"; width: 36; onClicked: page.zoomBy(1.2) }
            }
        }

        Flickable {
            id: flick
            anchors { top: bar.bottom; left: parent.left; right: parent.right; bottom: parent.bottom }
            clip: true
            contentWidth: Math.max(width, page.designW * page.zoom)
            contentHeight: Math.max(height, page.designH * page.zoom)
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }
            ScrollBar.horizontal: ScrollBar { policy: ScrollBar.AsNeeded }

            WheelHandler {
                acceptedModifiers: Qt.ControlModifier
                onWheel: (e) => page.zoomBy(e.angleDelta.y > 0 ? 1.1 : 1 / 1.1)
            }

            Item {
                id: board
                objectName: "board"
                width: page.designW; height: page.designH
                x: Math.max(0, (flick.width - width * page.zoom) / 2)
                transformOrigin: Item.TopLeft
                scale: page.zoom

                // connectors
                Repeater {
                    model: page.rounds
                    delegate: Item {
                        id: lineCol
                        required property int index
                        readonly property int r: index
                        Repeater {
                            model: Math.pow(2, page.rounds - lineCol.r - 1)
                            delegate: Shape {
                                id: conn
                                required property int index
                                readonly property int w: { win.bracket.revision; return win.bracket.winner(lineCol.r, index) }
                                readonly property bool bye: lineCol.r === 0 && win.bracket.isBye(index)
                                readonly property real xe: page.colX(lineCol.r) + page.boxW
                                readonly property real xm: xe + (page.colW - page.boxW) / 2
                                readonly property real xn: page.colX(lineCol.r + 1)
                                readonly property real ya: page.slotTop(lineCol.r, 2 * index) + page.boxH / 2
                                readonly property real yb: page.slotTop(lineCol.r, 2 * index + 1) + page.boxH / 2
                                readonly property real ym: (ya + yb) / 2
                                preferredRendererType: Shape.CurveRenderer
                                ShapePath {
                                    strokeColor: conn.w === 0 && !conn.bye ? "#16a34a" : "#b8c0ca"
                                    strokeWidth: conn.w === 0 && !conn.bye ? 3 : 2
                                    strokeStyle: conn.bye && conn.w !== 0 ? ShapePath.DashLine : ShapePath.SolidLine
                                    fillColor: "transparent"
                                    PathPolyline { path: [Qt.point(conn.xe, conn.ya), Qt.point(conn.xm, conn.ya), Qt.point(conn.xm, conn.ym)] }
                                }
                                ShapePath {
                                    strokeColor: conn.w === 1 && !conn.bye ? "#16a34a" : "#b8c0ca"
                                    strokeWidth: conn.w === 1 && !conn.bye ? 3 : 2
                                    strokeStyle: conn.bye && conn.w !== 1 ? ShapePath.DashLine : ShapePath.SolidLine
                                    fillColor: "transparent"
                                    PathPolyline { path: [Qt.point(conn.xe, conn.yb), Qt.point(conn.xm, conn.yb), Qt.point(conn.xm, conn.ym)] }
                                }
                                ShapePath {
                                    strokeColor: conn.w >= 0 && !conn.bye ? "#16a34a" : "#b8c0ca"
                                    strokeWidth: conn.w >= 0 && !conn.bye ? 3 : 2
                                    fillColor: "transparent"
                                    PathPolyline { path: [Qt.point(conn.xm, conn.ym), Qt.point(conn.xn, conn.ym)] }
                                }
                            }
                        }
                    }
                }

                // round headers + slots
                Repeater {
                    model: page.rounds > 0 ? page.rounds + 1 : 0
                    delegate: Item {
                        id: col
                        required property int index
                        readonly property int r: index
                        readonly property bool isChampion: r === page.rounds
                        readonly property var names: { win.bracket.revision; return win.bracket.slots(r) }

                        Text {
                            x: page.colX(col.r); y: 16; width: page.boxW
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
                                readonly property bool byeMatch: col.r === 0 && win.bracket.isBye(match)
                                readonly property bool isBye: col.r === 0 && name === ""
                                readonly property int result: { win.bracket.revision; return win.bracket.winner(col.r, match) }
                                readonly property bool won: result === side && !byeMatch
                                readonly property bool lost: result >= 0 && result !== side && !byeMatch
                                readonly property bool clickable: !col.isChampion && !byeMatch && name !== ""
                                    && col.names[2 * match] !== "" && col.names[2 * match + 1] !== ""
                                readonly property bool hot: mouse.containsMouse && clickable

                                x: page.colX(col.r); y: page.slotTop(col.r, index)
                                width: page.boxW; height: page.boxH; radius: 7
                                color: col.isChampion ? (name ? "#fff4c2" : "#fffbea")
                                     : won ? "#e8f8ee"
                                     : isBye ? "transparent"
                                     : name === "" ? "#f5f7fa"
                                     : hot ? "#eef4ff" : "#ffffff"
                                border.width: col.isChampion || won ? 2.5 : 1.5
                                border.color: col.isChampion ? "#d4a017"
                                            : won ? "#16a34a"
                                            : isBye ? "#d9dee4"
                                            : hot ? "#3b82f6" : "#b8c0ca"
                                opacity: lost ? 0.45 : 1

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    x: 12; width: parent.width - 24
                                    elide: Text.ElideRight
                                    text: slot.isBye ? "volno"
                                        : slot.name !== "" ? (col.isChampion ? "🏆 " + slot.name : slot.name)
                                        : col.isChampion ? "🏆 ?" : "?"
                                    font.pixelSize: page.compact ? 14 : 16
                                    font.bold: slot.name !== ""
                                    font.italic: slot.isBye
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
            }
        }
    }

    // ----------------------------------------------------------- button ----
    component AppButton: Rectangle {
        id: btn
        property string text
        property bool primary: false
        property bool danger: false
        signal clicked
        width: Math.max(90, label.implicitWidth + 28)
        height: 36
        radius: 7
        opacity: enabled ? 1 : 0.45
        color: danger ? "#dc2626" : primary ? (ma.containsMouse ? "#15803d" : "#16a34a")
             : ma.containsMouse ? "#eef2f6" : "#ffffff"
        border.color: danger ? "#dc2626" : primary ? "transparent" : "#b8c0ca"
        border.width: 1.5
        Text {
            id: label
            anchors.centerIn: parent
            text: btn.text
            font.pixelSize: 14
            font.bold: btn.primary || btn.danger
            color: btn.primary || btn.danger ? "#ffffff" : "#1f2933"
        }
        MouseArea {
            id: ma
            anchors.fill: parent
            hoverEnabled: true
            enabled: btn.enabled
            cursorShape: Qt.PointingHandCursor
            onClicked: btn.clicked()
        }
    }
}
