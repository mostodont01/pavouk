import os
import random

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF, Qt  # noqa: E402
from PySide6.QtQuick import QQuickWindow  # noqa: E402,F401  (wrap root as QQuickWindow)

from pavouk.app import create_engine, make_model  # noqa: E402
from pavouk.bracket import Bracket  # noqa: E402

TEAMS = ["Téčka", "Proherci", "Sumec", "Lopaty", "Robot", "Epongupa", "Smažáci", "Touchgrass lidi"]


def _setup(qtbot, tmp_path, bracket=None, seed=1):
    state = tmp_path / "state.json"
    model = make_model(bracket, state, rng=random.Random(seed))
    engine = create_engine(model)
    roots = engine.rootObjects()
    assert roots, "QML failed to load"
    win = roots[0]
    win.show()
    qtbot.waitExposed(win)
    qtbot.wait(200)  # let the first layout/polish pass settle (zoom, centering)
    return model, engine, win, state


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
    assert item.isVisible(), name
    p = item.mapToScene(QPointF(item.width() / 2, item.height() / 2)).toPoint()
    qtbot.mouseClick(win, Qt.LeftButton, pos=p)
    qtbot.wait(30)


def _start(qtbot, win, names):
    _find(win, "namesInput").setProperty("text", "\n".join(names))
    qtbot.wait(10)
    _click(qtbot, win, "startButton")


def test_intro_then_draw_and_play(qtbot, tmp_path):
    model, engine, win, state = _setup(qtbot, tmp_path)
    assert _find(win, "intro").isVisible()
    assert not _find(win, "bracketPage").isVisible()

    _start(qtbot, win, TEAMS)
    assert model.property("started")
    assert _find(win, "bracketPage").isVisible()
    assert state.exists()

    placed = [_find(win, f"slot_0_{i}").property("name") for i in range(8)]
    assert sorted(placed) == sorted(TEAMS)

    for r, n in [(0, 4), (1, 2), (2, 1)]:
        for m in range(n):
            _click(qtbot, win, f"slot_{r}_{2 * m}")
    champ = model.property("champion")
    assert champ == placed[0]
    assert _find(win, "slot_3_0").property("name") == champ


def test_invalid_input_blocks_start(qtbot, tmp_path):
    model, engine, win, state = _setup(qtbot, tmp_path)
    _start(qtbot, win, ["jen jeden"])
    assert not model.property("started")
    _start(qtbot, win, ["A", "B", "a"])
    assert not model.property("started")


def test_odd_count_gets_byes(qtbot, tmp_path):
    model, engine, win, state = _setup(qtbot, tmp_path)
    _start(qtbot, win, TEAMS[:5])
    slots = [_find(win, f"slot_0_{i}").property("name") for i in range(8)]
    assert slots.count("") == 3
    b = Bracket.load(state)
    assert sorted(b.names) == sorted(TEAMS[:5])
    # bye winners are already in round 2
    assert sum(1 for i in range(4) if _find(win, f"slot_1_{i}").property("name")) == 3


def test_hundred_teams_render(qtbot, tmp_path):
    model, engine, win, state = _setup(qtbot, tmp_path)
    _start(qtbot, win, [f"Tým {i}" for i in range(1, 101)])
    assert model.property("rounds") == 7
    assert _find(win, "slot_0_127") is not None
    assert _find(win, "slot_7_0") is not None


def test_resume_saved_and_back_to_intro(qtbot, tmp_path):
    b = Bracket(TEAMS)
    b.pick(0, 0, 1)
    model, engine, win, state = _setup(qtbot, tmp_path, bracket=b)
    assert _find(win, "bracketPage").isVisible()
    assert _find(win, "slot_1_0").property("name") == "Proherci"

    _click(qtbot, win, "backButton")
    assert _find(win, "intro").isVisible()
    assert _find(win, "namesInput").property("text") == "\n".join(TEAMS)
    _click(qtbot, win, "resumeButton")
    assert _find(win, "slot_1_0").property("name") == "Proherci"


def test_reset_needs_two_clicks(qtbot, tmp_path):
    model, engine, win, state = _setup(qtbot, tmp_path, bracket=Bracket(TEAMS))
    _click(qtbot, win, "slot_0_0")
    _click(qtbot, win, "resetButton")
    assert _find(win, "slot_1_0").property("name") == "Téčka"
    _click(qtbot, win, "resetButton")
    assert _find(win, "slot_1_0").property("name") == ""
