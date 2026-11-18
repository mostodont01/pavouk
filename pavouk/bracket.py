"""Single-elimination bracket logic (no UI)."""

from __future__ import annotations

import json
import random
from pathlib import Path

MIN_TEAMS = 2
MAX_TEAMS = 128


class Bracket:
    """A knockout bracket.

    ``teams`` has a power-of-two length; ``None`` in it is a bye (*volno*):
    the team paired with it advances automatically. Two byes can't meet.

    ``winners[r][m]`` is the winning side of match ``m`` in round ``r``:
    0 = the upper slot, 1 = the lower slot, ``None`` = not played yet.
    """

    def __init__(self, teams: list[str | None]):
        teams = list(teams)
        n = len(teams)
        if n < 2 or n & (n - 1):
            raise ValueError(f"number of slots must be a power of two, got {n}")
        for m in range(n // 2):
            if teams[2 * m] is None and teams[2 * m + 1] is None:
                raise ValueError("two byes in one match")
        self.teams = teams
        self.winners: list[list[int | None]] = []
        matches = n // 2
        while matches >= 1:
            self.winners.append([None] * matches)
            matches //= 2
        self._apply_byes()

    @classmethod
    def draw(cls, names: list[str], rng: random.Random | None = None) -> "Bracket":
        """Randomly place ``names`` into a bracket, adding byes if needed."""
        rng = rng or random.Random()
        names = list(names)
        if not MIN_TEAMS <= len(names) <= MAX_TEAMS:
            raise ValueError(f"need {MIN_TEAMS}–{MAX_TEAMS} teams, got {len(names)}")
        size = 1
        while size < len(names):
            size *= 2
        rng.shuffle(names)
        byes = size - len(names)
        matches: list[list[str | None]] = []
        it = iter(names)
        for m in range(size // 2):
            if m < byes:
                matches.append([next(it), None])
            else:
                matches.append([next(it), next(it)])
        rng.shuffle(matches)
        for pair in matches:  # bye on a random side
            if pair[1] is None and rng.random() < 0.5:
                pair.reverse()
        return cls([t for pair in matches for t in pair])

    def _apply_byes(self) -> None:
        for m in range(len(self.winners[0])):
            a, b = self.teams[2 * m], self.teams[2 * m + 1]
            if a is None or b is None:
                self.winners[0][m] = 0 if b is None else 1

    def is_bye(self, match: int) -> bool:
        """Is first-round match ``match`` a bye (decided automatically)?"""
        return self.teams[2 * match] is None or self.teams[2 * match + 1] is None

    @property
    def names(self) -> list[str]:
        return [t for t in self.teams if t is not None]

    @property
    def rounds(self) -> int:
        return len(self.winners)

    def slots(self, rnd: int) -> list[str | None]:
        """Team names in round ``rnd``'s slots.

        In round 0, ``None`` is a bye; in later rounds it means "not decided
        yet". ``rnd == rounds`` gives the champion slot.
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
        if rnd == 0 and self.is_bye(match):
            return False
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
        """Clear all results (byes stay)."""
        for rnd in self.winners:
            rnd[:] = [None] * len(rnd)
        self._apply_byes()

    # --- persistence -------------------------------------------------------

    def to_dict(self) -> dict:
        return {"teams": self.teams, "winners": self.winners}

    @classmethod
    def from_dict(cls, data: dict) -> "Bracket":
        b = cls(data["teams"])
        winners = data.get("winners", [])
        if [len(r) for r in winners] == [len(r) for r in b.winners]:
            b.winners = [[w if w in (0, 1) else None for w in r] for r in winners]
            b._apply_byes()
        return b

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=1), "utf-8")

    @classmethod
    def load(cls, path: Path) -> "Bracket | None":
        """Saved bracket, or ``None`` if missing or broken."""
        try:
            return cls.from_dict(json.loads(path.read_text("utf-8")))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def text(self) -> str:
        """Plain-text overview (for the CLI)."""
        lines = []
        for r in range(self.rounds):
            slots = self.slots(r)
            lines.append(round_name(r, self.rounds) + ":")
            for m, w in enumerate(self.winners[r]):
                if r == 0 and self.is_bye(m):
                    lines.append(f"  {slots[2 * m + w]} (volno)")
                    continue
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


def parse_names(text: str) -> tuple[list[str], str]:
    """Team names from text (one per line). Returns (names, error or "")."""
    names = [ln.strip() for ln in text.splitlines()]
    names = [n for n in names if n]
    if len(names) < MIN_TEAMS:
        return names, f"Zadej aspoň {MIN_TEAMS} týmy."
    if len(names) > MAX_TEAMS:
        return names, f"Maximálně {MAX_TEAMS} týmů."
    seen = set()
    for n in names:
        key = n.casefold()
        if key in seen:
            return names, f"Tým „{n}“ je tam dvakrát."
        seen.add(key)
    return names, ""
