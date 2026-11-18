"""Pavouk: clickable tournament bracket (PySide6 + QML) and a small CLI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .bracket import DEFAULT_TEAMS, Bracket, read_teams, round_name

HERE = Path(__file__).resolve().parent


def app_dir() -> Path:
    """Folder of the .exe when frozen, else the current folder."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def teams_file() -> Path:
    return app_dir() / "tymy.txt"


def load_teams(path: Path | None = None) -> list[str]:
    path = path or teams_file()
    teams = read_teams(path)
    if teams is None:
        teams = list(DEFAULT_TEAMS)
        try:  # leave an editable list next to the app
            if not path.exists():
                path.write_text("\n".join(teams) + "\n", "utf-8")
        except OSError:
            pass
    return teams


def default_state_file() -> Path:
    from PySide6.QtCore import QStandardPaths

    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    return Path(base or Path.home() / ".pavouk") / "pavouk.json"


def make_model(bracket: Bracket, state_file: Path | None):
    from PySide6.QtCore import Property, QObject, Signal, Slot

    class BracketModel(QObject):
        changed = Signal()

        def __init__(self):
            super().__init__()
            self._b = bracket
            self._rev = 0

        def _touch(self):
            self._rev += 1
            if state_file is not None:
                try:
                    self._b.save(state_file)
                except OSError as e:
                    print(f"pavouk: cannot save {state_file}: {e}", file=sys.stderr)
            self.changed.emit()

        @Property(int, notify=changed)
        def revision(self):
            return self._rev

        @Property(int, constant=True)
        def rounds(self):
            return self._b.rounds

        @Property(str, notify=changed)
        def champion(self):
            return self._b.champion or ""

        @Slot(int, result="QVariantList")
        def slots(self, rnd):
            return [s or "" for s in self._b.slots(rnd)]

        @Slot(int, int, result=int)
        def winner(self, rnd, match):
            if rnd >= self._b.rounds:
                return -1
            w = self._b.winners[rnd][match]
            return -1 if w is None else w

        @Slot(int, result=str)
        def roundName(self, rnd):
            if rnd >= self._b.rounds:
                return "Vítěz"
            return round_name(rnd, self._b.rounds)

        @Slot(int, int, int)
        def pick(self, rnd, match, side):
            if self._b.pick(rnd, match, side):
                self._touch()

        @Slot()
        def reset(self):
            self._b.reset()
            self._touch()

    return BracketModel()


def create_engine(model):
    from PySide6.QtQml import QQmlApplicationEngine

    engine = QQmlApplicationEngine()
    engine.setInitialProperties({"bracket": model})
    engine.load(str(HERE / "Main.qml"))
    return engine


def run_gui(teams_path: Path | None, state_file: Path | None) -> int:
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Pavouk")
    app.setOrganizationName("Pavouk")
    teams = load_teams(teams_path)
    state_file = state_file or default_state_file()
    model = make_model(Bracket.load(state_file, teams), state_file)
    engine = create_engine(model)
    if not engine.rootObjects():
        return 1
    return app.exec()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="pavouk", description="Klikací turnajový pavouk.")
    p.add_argument("--tymy", type=Path, help="soubor s týmy (jeden na řádek), výchozí tymy.txt")
    p.add_argument("--stav", type=Path, help="soubor s uloženými výsledky")
    p.add_argument("--vypis", action="store_true", help="jen vypsat pavouka do terminálu")
    args = p.parse_args(argv)
    if args.vypis:
        teams = load_teams(args.tymy)
        b = Bracket.load(args.stav, teams) if args.stav else Bracket(teams)
        print(b.text())
        return 0
    return run_gui(args.tymy, args.stav)


if __name__ == "__main__":
    sys.exit(main())
