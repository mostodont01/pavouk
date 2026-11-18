import pytest

from pavouk.bracket import DEFAULT_TEAMS, Bracket, read_teams, round_name


def test_rounds_and_slots():
    b = Bracket()
    assert b.rounds == 3
    assert b.slots(0) == DEFAULT_TEAMS
    assert b.slots(1) == [None] * 4
    assert b.champion is None


def test_rejects_non_power_of_two():
    with pytest.raises(ValueError):
        Bracket(["a", "b", "c"])


def test_full_tournament():
    b = Bracket(list("ABCDEFGH"))
    for m, side in enumerate([0, 1, 0, 1]):
        assert b.pick(0, m, side)
    assert b.slots(1) == ["A", "D", "E", "H"]
    b.pick(1, 0, 1)
    b.pick(1, 1, 0)
    assert b.slots(2) == ["D", "E"]
    b.pick(2, 0, 1)
    assert b.champion == "E"


def test_cannot_pick_before_opponents_known():
    b = Bracket(list("ABCDEFGH"))
    b.pick(0, 0, 0)
    assert not b.pick(1, 0, 0)  # M2 not played yet
    assert b.winners[1][0] is None


def test_click_again_clears():
    b = Bracket(list("ABCDEFGH"))
    b.pick(0, 0, 0)
    b.pick(0, 0, 0)
    assert b.winners[0][0] is None


def test_changing_result_clears_later_rounds():
    b = Bracket(list("ABCDEFGH"))
    for m in range(4):
        b.pick(0, m, 0)
    b.pick(1, 0, 0)
    b.pick(1, 1, 0)
    b.pick(2, 0, 0)
    assert b.champion == "A"
    b.pick(0, 0, 1)  # B beat A after all
    assert b.slots(1)[0] == "B"
    assert b.winners[1] == [None, 0]  # other semifinal kept
    assert b.champion is None


def test_save_load_roundtrip(tmp_path):
    f = tmp_path / "s" / "state.json"
    b = Bracket()
    b.pick(0, 2, 1)
    b.save(f)
    b2 = Bracket.load(f, DEFAULT_TEAMS)
    assert b2.winners == b.winners


def test_load_with_changed_teams_starts_fresh(tmp_path):
    f = tmp_path / "state.json"
    b = Bracket()
    b.pick(0, 0, 0)
    b.save(f)
    b2 = Bracket.load(f, list("ABCDEFGH"))
    assert b2.teams == list("ABCDEFGH")
    assert b2.winners[0][0] is None


def test_load_broken_file(tmp_path):
    f = tmp_path / "state.json"
    f.write_text("{nope")
    assert Bracket.load(f, DEFAULT_TEAMS).winners[0] == [None] * 4


def test_read_teams(tmp_path):
    f = tmp_path / "tymy.txt"
    f.write_text("﻿A\n\n B \nC\nD\n", "utf-8")
    assert read_teams(f) == ["A", "B", "C", "D"]
    assert read_teams(tmp_path / "missing.txt") is None


def test_round_names():
    assert [round_name(r, 3) for r in range(3)] == ["Čtvrtfinále", "Semifinále", "Finále"]


def test_text_output():
    b = Bracket()
    b.pick(0, 0, 1)
    t = b.text()
    assert "Téčka vs Proherci  -> Proherci" in t
    assert "Vítěz: ?" in t
