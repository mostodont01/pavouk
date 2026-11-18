import random

import pytest

from pavouk.bracket import MAX_TEAMS, Bracket, parse_names, round_name

EIGHT = list("ABCDEFGH")


def test_rounds_and_slots():
    b = Bracket(EIGHT)
    assert b.rounds == 3
    assert b.slots(0) == EIGHT
    assert b.slots(1) == [None] * 4
    assert b.champion is None


def test_rejects_bad_sizes_and_double_bye():
    with pytest.raises(ValueError):
        Bracket(["a", "b", "c"])
    with pytest.raises(ValueError):
        Bracket(["a", "b", None, None])


def test_full_tournament():
    b = Bracket(EIGHT)
    for m, side in enumerate([0, 1, 0, 1]):
        assert b.pick(0, m, side)
    assert b.slots(1) == ["A", "D", "E", "H"]
    b.pick(1, 0, 1)
    b.pick(1, 1, 0)
    assert b.slots(2) == ["D", "E"]
    b.pick(2, 0, 1)
    assert b.champion == "E"


def test_cannot_pick_before_opponents_known():
    b = Bracket(EIGHT)
    b.pick(0, 0, 0)
    assert not b.pick(1, 0, 0)
    assert b.winners[1][0] is None


def test_click_again_clears():
    b = Bracket(EIGHT)
    b.pick(0, 0, 0)
    b.pick(0, 0, 0)
    assert b.winners[0][0] is None


def test_changing_result_clears_later_rounds():
    b = Bracket(EIGHT)
    for m in range(4):
        b.pick(0, m, 0)
    b.pick(1, 0, 0)
    b.pick(1, 1, 0)
    b.pick(2, 0, 0)
    assert b.champion == "A"
    b.pick(0, 0, 1)
    assert b.slots(1)[0] == "B"
    assert b.winners[1] == [None, 0]
    assert b.champion is None


# --- byes -----------------------------------------------------------------

def test_bye_advances_automatically_and_cannot_be_clicked():
    b = Bracket(["A", None, "B", "C"])
    assert b.is_bye(0) and not b.is_bye(1)
    assert b.slots(1) == ["A", None]
    assert not b.pick(0, 0, 0)
    assert not b.pick(0, 0, 1)
    b.pick(0, 1, 1)
    b.pick(1, 0, 1)
    assert b.champion == "C"


def test_bye_on_upper_side():
    b = Bracket([None, "A", "B", "C"])
    assert b.slots(1)[0] == "A"


def test_reset_keeps_byes():
    b = Bracket(["A", None, "B", "C"])
    b.pick(0, 1, 0)
    b.reset()
    assert b.winners[0] == [0, None]


@pytest.mark.parametrize("n", [2, 3, 5, 7, 8, 9, 17, 100, MAX_TEAMS])
def test_draw_any_count(n):
    names = [f"T{i}" for i in range(n)]
    b = Bracket.draw(names, random.Random(n))
    size = len(b.teams)
    assert size >= n and size & (size - 1) == 0 and size < 2 * n
    assert sorted(b.names) == sorted(names)
    assert b.teams.count(None) == size - n
    for r in range(b.rounds):
        for m in range(len(b.winners[r])):
            if b.winners[r][m] is None:
                assert b.pick(r, m, 0)
    assert b.champion in names


def test_draw_is_random():
    names = [f"T{i}" for i in range(8)]
    draws = {tuple(Bracket.draw(names, random.Random(s)).teams) for s in range(10)}
    assert len(draws) > 1


def test_draw_limits():
    with pytest.raises(ValueError):
        Bracket.draw(["solo"])
    with pytest.raises(ValueError):
        Bracket.draw([str(i) for i in range(MAX_TEAMS + 1)])


# --- persistence / text -------------------------------------------------------

def test_save_load_roundtrip(tmp_path):
    f = tmp_path / "s" / "state.json"
    b = Bracket.draw(["Téčka", "Proherci", "Sumec", "Lopaty", "Robot"], random.Random(1))
    m = next(i for i in range(len(b.winners[0])) if not b.is_bye(i))
    b.pick(0, m, 1)
    b.save(f)
    b2 = Bracket.load(f)
    assert b2.teams == b.teams
    assert b2.winners == b.winners


def test_load_missing_or_broken(tmp_path):
    assert Bracket.load(tmp_path / "nope.json") is None
    f = tmp_path / "state.json"
    f.write_text("{nope")
    assert Bracket.load(f) is None


def test_parse_names():
    assert parse_names("﻿ A \n\n B\nC\n") == (["﻿ A".strip(), "B", "C"], "") or \
        parse_names(" A \n\n B\nC\n") == (["A", "B", "C"], "")
    assert parse_names(" A \n\n B\nC\n") == (["A", "B", "C"], "")
    assert parse_names("A")[1]
    assert "dvakrát" in parse_names("A\nB\na")[1]
    assert parse_names("\n".join(str(i) for i in range(MAX_TEAMS + 1)))[1]


def test_round_names():
    assert [round_name(r, 3) for r in range(3)] == ["Čtvrtfinále", "Semifinále", "Finále"]
    assert round_name(0, 7) == "1. kolo"


def test_text_output():
    b = Bracket(["A", None, "B", "C"])
    b.pick(0, 1, 1)
    t = b.text()
    assert "A (volno)" in t
    assert "B vs C  -> C" in t
    assert "Vítěz: ?" in t
