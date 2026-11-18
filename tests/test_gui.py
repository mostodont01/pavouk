import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtQuick import QQuickItem  # noqa: E402

from pavouk.app import create_engine, make_model  # noqa: E402
from pavouk.bracket import Bracket  # noqa: E402


def _setup(qtbot, tmp_path):
    state = tmp_path / "state.json"
    b = Bracket()
    model = make_model(b, state)
    engine = create_engine(model)
    roots = engine.rootObjects()
    assert roots, "QML failed to load"
    win = roots[0]
    win.show()
    qtbot.waitExposed(win)
    return b, model, engine, win, state


def _find(win, name):
    stack = [win.contentItem()]
    while stack:
        it = stack.pop()
        if it.objectName() == name:
            return it
        stack.extend(it.childItems())
    return None


def _click(qtbot, win, name):
    item = _find(win, name)
    assert item is not None, name
    p = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
    qtbot.mouseClick(win, Qt.LeftButton, pos=p)
    qtbot.wait(20)


def test_qml_loads_and_click_advances(qtbot, tmp_path):
    b, model, engine, win, state = _setup(qtbot, tmp_path)
    assert _find(win, "slot_0_7").property("name") == "Touchgrass lidi"

    _click(qtbot, win, "slot_0_1")  # Proherci beat Téčka
    assert b.winners[0][0] == 1
    assert _find(win, "slot_1_0").property("name") == "Proherci"
    assert state.exists()  # autosaved

    # play it out: top teams always win
    for name in ["slot_0_2", "slot_0_4", "slot_0_6", "slot_1_0", "slot_1_2", "slot_2_0"]:
        _click(qtbot, win, name)
    assert b.champion == "Proherci"
    assert model.property("champion") == "Proherci"
    assert _find(win, "slot_3_0").property("name") == "Proherci"


def test_reset_needs_two_clicks(qtbot, tmp_path):
    b, model, engine, win, state = _setup(qtbot, tmp_path)
    _click(qtbot, win, "slot_0_0")
    _click(qtbot, win, "resetButton")
    assert b.winners[0][0] == 0
    _click(qtbot, win, "resetButton")
    assert b.winners[0][0] is None
