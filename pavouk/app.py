"""Pavouk: clickable tournament bracket (PySide6 + QML) and a small CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bracket import MAX_TEAMS, Bracket, parse_names, round_name

HERE = Path(__file__).resolve().parent


def default_state_file() -> Path:
    from PySide6.QtCore import QStandardPaths

    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    return Path(base or Path.home() / ".pavouk") / "pavouk.json"


def make_model(bracket: Bracket | None, state_file: Path | None, rng=None):
    """QML-facing model. ``bracket=None`` starts on the intro screen."""
    from PySide6.QtCore import Property, QObject, Signal, Slot

    class BracketModel(QObject):
        changed = Signal()

        def __init__(self):
            super().__init__()
            self._b = bracket
            self._started = bracket is not None
            self._last_names = bracket.names if bracket else []
            self._rev = 0

        def _touch(self):
            self._rev += 1
            if state_file is not None and self._b is not None:
                try:
                    self._b.save(state_file)
                except OSError as e:
                    print(f"pavouk: cannot save {state_file}: {e}", file=sys.stderr)
            self.changed.emit()

        @Property(int, notify=changed)
        def revision(self):
            return self._rev

        @Property(bool, notify=changed)
        def started(self):
            return self._started

        @Property(int, notify=changed)
        def rounds(self):
            return self._b.rounds if self._b else 0

        @Property(str, notify=changed)
        def champion(self):
            return (self._b.champion or "") if self._b else ""

        @Property(str, notify=changed)
        def lastNames(self):
            return "\n".join(self._last_names)

        @Property(int, constant=True)
        def maxTeams(self):
            return MAX_TEAMS

        @Slot(str, result=str)
        def check(self, text):
            """Validation message for the intro screen ("" = OK)."""
            return parse_names(text)[1]

        @Slot(str, result=int)
        def count(self, text):
            return len(parse_names(text)[0])

        @Slot(str, result=str)
        def start(self, text):
            """Draw a new bracket from the names. Returns an error or ""."""
            names, err = parse_names(text)
            if err:
                return err
            self._b = Bracket.draw(names, rng)
            self._last_names = names
            self._started = True
            self._touch()
            return ""

        @Slot()
        def backToIntro(self):
            self._started = False
            self._rev += 1
            self.changed.emit()

        @Slot()
        def resume(self):
            if self._b is not None:
                self._started = True
                self._rev += 1
                self.changed.emit()

        @Property(bool, notify=changed)
        def canResume(self):
            return self._b is not None and not self._started

        @Slot(int, result="QVariantList")
        def slots(self, rnd):
            if self._b is None:
                return []
            return [s or "" for s in self._b.slots(rnd)]

        @Slot(int, result=bool)
        def isBye(self, match):
            return self._b is not None and self._b.is_bye(match)

        @Slot(int, int, result=int)
        def winner(self, rnd, match):
            if self._b is None or rnd >= self._b.rounds:
                return -1
            w = self._b.winners[rnd][match]
            return -1 if w is None else w

        @Slot(int, result=str)
        def roundName(self, rnd):
            if self._b is None:
                return ""
            if rnd >= self._b.rounds:
                return "Vítěz"
            return round_name(rnd, self._b.rounds)

        @Slot(int, int, int)
        def pick(self, rnd, match, side):
            if self._b is not None and self._b.pick(rnd, match, side):
                self._touch()

        @Slot()
        def reset(self):
            if self._b is not None:
                self._b.reset()
                self._touch()

    return BracketModel()


def create_engine(model):
    from PySide6.QtQml import QQmlApplicationEngine

    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"bracket": model})
    engine.load(str(HERE / "Main.qml"))
    return engine


def run_gui(state_file: Path | None, smoke: bool = False) -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Pavouk")
    app.setOrganizationName("Pavouk")
    state_file = state_file or default_state_file()
    model = make_model(Bracket.load(state_file), state_file)
    engine = create_engine(model)
    if not engine.rootObjects():
        return 1
    if smoke:  # CI: start, show the window, quit
        QTimer.singleShot(1500, app.quit)
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pavouk", description="Klikací turnajový pavouk.")
    p.add_argument("--stav", type=Path, help="soubor s uloženým turnajem")
    p.add_argument("--vypis", action="store_true", help="vypsat uložený turnaj do terminálu")
    p.add_argument("--los", type=Path, metavar="TYMY.txt",
                   help="vylosovat nového pavouka z týmů v souboru (jeden na řádek) a vypsat ho")
    p.add_argument("--smoke", action="store_true", help=argparse.SUPPRESS)
    args = p.parse_args(argv)
    if args.los:
        names, err = parse_names(args.los.read_text("utf-8-sig"))
        if err:
            print(err, file=sys.stderr)
            return 2
        b = Bracket.draw(names)
        if args.stav:
            b.save(args.stav)
        print(b.text())
        return 0
    if args.vypis:
        if not args.stav:
            print("--vypis potřebuje --stav SOUBOR", file=sys.stderr)
            return 2
        b = Bracket.load(args.stav)
        print(b.text() if b else "Žádný uložený turnaj.")
        return 0
    return run_gui(args.stav, args.smoke)


if __name__ == "__main__":
    sys.exit(main())
