"""Tests for the pure rule engine — no ephemeris required."""

from datetime import datetime, timedelta

import pytest

from pranic_current.swara import (
    DEFAULT, Config, paksha_and_tithi, state_at, sunrise_svara,
    tattva_windows, timeline,
)

SR = datetime(2026, 7, 13, 6, 0)


# ---- Rule A: the sunrise current ----

@pytest.mark.parametrize("idx,expect", [
    (0, "ida"),      # shukla 1
    (2, "ida"),      # shukla 3
    (3, "pingala"),  # shukla 4
    (5, "pingala"),  # shukla 6
    (6, "ida"),      # shukla 7
    (9, "pingala"),  # shukla 10
    (12, "ida"),     # shukla 13
    (14, "ida"),     # purnima
    (15, "pingala"), # krishna 1  — reversed
    (18, "ida"),     # krishna 4  — reversed
    (29, "pingala"), # amavasya   — reversed
])
def test_sunrise_svara(idx, expect):
    assert sunrise_svara(idx) == expect


def test_paksha():
    assert paksha_and_tithi(0) == ("shukla", 1)
    assert paksha_and_tithi(14) == ("shukla", 15)
    assert paksha_and_tithi(15) == ("krishna", 1)
    assert paksha_and_tithi(29) == ("krishna", 15)


# ---- Rule B: alternation ----

def test_alternates_hourly():
    seq = [state_at(SR + timedelta(minutes=30 + 60 * i), SR, 0).svara.key
           for i in range(5)]
    assert seq == ["ida", "pingala", "ida", "pingala", "ida"]


def test_alternation_continues_through_the_night():
    # 13 hours after sunrise -> block 13 (odd) -> the opposite current
    st = state_at(SR + timedelta(hours=13, minutes=30), SR, 0)
    assert st.svara.key == "pingala"


# ---- Rule D: tattvas ----

def test_windows_fill_the_block():
    w = tattva_windows(DEFAULT)
    assert [x[0] for x in w] == ["prithvi", "jala", "agni", "vayu", "akasha"]
    assert w[-1][2] == 60
    assert [round(e - s) for _, s, e in w] == [20, 16, 12, 8, 4]


@pytest.mark.parametrize("mins,expect", [
    (0, "prithvi"), (19.9, "prithvi"),
    (20, "jala"), (35.9, "jala"),
    (36, "agni"), (47.9, "agni"),
    (48, "vayu"), (55.9, "vayu"),
    (56, "akasha"), (59.9, "akasha"),
])
def test_tattva_boundaries(mins, expect):
    assert state_at(SR + timedelta(minutes=mins), SR, 0).tattva.key == expect


def test_windows_rescale_with_period():
    w = tattva_windows(Config(swara_period=90))
    assert w[-1][2] == pytest.approx(90)
    assert w[0][2] == pytest.approx(30)   # 20 min * 1.5


# ---- Rule C: sushumna ----

def test_sushumna_straddles_the_change():
    assert state_at(SR + timedelta(minutes=59), SR, 0).sushumna       # -1 min
    assert state_at(SR + timedelta(minutes=61), SR, 0).sushumna       # +1 min
    assert not state_at(SR + timedelta(minutes=30), SR, 0).sushumna
    st = state_at(SR + timedelta(minutes=59), SR, 0)
    assert st.effective_svara.key == "sushumna"
    assert st.svara.key == "ida"          # underlying current still reported


# ---- timeline ----

def test_timeline_counts_one_vedic_day():
    ev = timeline(SR, 0, SR, SR + timedelta(days=1))
    assert sum(1 for e in ev if e.kind == "svara") == 24
    assert sum(1 for e in ev if e.kind == "tattva") == 24 * 4
    assert all(a.when <= b.when for a, b in zip(ev, ev[1:]))


def test_timeline_matches_state_at():
    for e in timeline(SR, 0, SR, SR + timedelta(hours=6)):
        if e.kind in ("svara", "tattva"):
            st = state_at(e.when + timedelta(seconds=30), SR, 0)
            assert (st.svara.key, st.tattva.key) == (e.svara, e.tattva)


def test_rejects_time_before_sunrise():
    with pytest.raises(ValueError):
        state_at(SR - timedelta(minutes=1), SR, 0)
