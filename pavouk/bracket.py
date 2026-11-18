"""Single-elimination bracket logic (no UI)."""

from __future__ import annotations

import json
from pathlib import Path

DEFAULT_TEAMS = [
    "Téčka",
    "Proherci",
    "Sumec",
    "Lopaty",
    "Robot",
    "Epongupa",
    "Smažáci",
    "Touchgrass lidi",
]


class Bracket:
    """A knockout bracket for 2^n teams.

    ``winners[r][m]`` is the winning side of match ``m`` in round ``r``:
    0 = the upper slot, 1 = the lower slot, ``None`` = not played yet.
    """

    def __init__(self, teams: list[str] | None = None):
        teams = list(teams or DEFAULT_TEAMS)
        n = len(teams)
        if n < 2 or n & (n - 1):
            raise ValueError(f"number of teams must be a power of two, got {n}")
        self.teams = teams
        self.winners: list[list[int | None]] = []
        matches = n // 2
        while matches >= 1:
            self.winners.append([None] * matches)
            matches //= 2

    @property
    def rounds(self) -> int:
        return len(self.winners)

    def slots(self, rnd: int) -> list[str | None]:
        """Team names in round ``rnd``'s slots (``None`` = not decided yet).

        ``rnd == rounds`` gives the champion slot.
        """
        if rnd == 0:
            return list(self.teams)
        prev = self.slots(rnd - 1)
        out: list[str | None] = []
        for m, w in enumerate(self.winners[rnd - 1]):
            out.append(None if w is None else prev[2 * m + w])
        return out

    @property
    def champion(self) -> str | None:
        return self.slots(self.rounds)[0]

    def pick(self, rnd: int, match: int, side: int) -> bool:
        """Mark ``side`` (0/1) as the winner of a match.

        Picking the current winner again clears the result. Changing a result
        clears the later matches that depended on it. Returns True if
        anything changed.
        """
        if side not in (0, 1):
            raise ValueError("side must be 0 or 1")
        slots = self.slots(rnd)
        if slots[2 * match] is None or slots[2 * match + 1] is None:
            return False  # both opponents must be known
        new = None if self.winners[rnd][match] == side else side
        self.winners[rnd][match] = new
        m = match
        for r in range(rnd + 1, self.rounds):
            m //= 2
            self.winners[r][m] = None
        return True

    def reset(self) -> None:
        for rnd in self.winners:
            rnd[:] = [None] * len(rnd)

    # --- persistence -------------------------------------------------------

    def to_dict(self) -> dict:
        return {"teams": self.teams, "winners": self.winners}

    @classmethod
    def from_dict(cls, data: dict) -> "Bracket":
        b = cls(data["teams"])
        winners = data.get("winners", [])
        if [len(r) for r in winners] == [len(r) for r in b.winners]:
            b.winners = [[w if w in (0, 1) else None for w in r] for r in winners]
        return b

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), "utf-8")

    @classmethod
    def load(cls, path: Path, teams: list[str]) -> "Bracket":
        """Load saved results; start fresh if missing, broken or the teams changed."""
        try:
            b = cls.from_dict(json.loads(path.read_text("utf-8")))
            if b.teams == teams:
                return b
        except (OSError, ValueError, KeyError, TypeError):
            pass
        return cls(teams)

    def text(self) -> str:
        """Plain-text overview (for the CLI)."""
        lines = []
        for r in range(self.rounds):
            slots = self.slots(r)
            lines.append(round_name(r, self.rounds) + ":")
            for m, w in enumerate(self.winners[r]):
                a, b = slots[2 * m] or "?", slots[2 * m + 1] or "?"
                res = "" if w is None else f"  -> {slots[2 * m + w]}"
                lines.append(f"  {a} vs {b}{res}")
        lines.append(f"Vítěz: {self.champion or '?'}")
        return "\n".join(lines)


def round_name(rnd: int, rounds: int) -> str:
    left = rounds - rnd  # 1 = final
    return {1: "Finále", 2: "Semifinále", 3: "Čtvrtfinále", 4: "Osmifinále"}.get(
        left, f"{rnd + 1}. kolo"
    )


def read_teams(path: Path) -> list[str] | None:
    """Team names from a text file, one per line (blank lines ignored)."""
    try:
        names = [ln.strip() for ln in path.read_text("utf-8-sig").splitlines()]
    except OSError:
        return None
    names = [n for n in names if n]
    return names or None
