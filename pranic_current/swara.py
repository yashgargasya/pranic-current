"""The svara engine.

Pure logic: given the sunrise of the vedic day and the tithi current at that
sunrise, it can name the prescribed current and element at any instant, and
enumerate every transition. No ephemeris is imported here — that keeps the
ritual rules testable and the astronomy swappable.

Rules implemented (see docs/svara_shastra.md):
  A. sunrise svara  = f(paksha, tithi)
  B. alternation    = every `swara_period` minutes from sunrise, day and night
  C. sushumna       = sandhi window straddling each svara change
  D. tattvas        = 20/16/12/8/4 min inside every svara block
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .tattva import SVARAS, TATTVAS, TATTVA_ORDERS, Svara, Tattva

# Tithis (numbered 1..15 within their own paksha) on which the LUNAR current
# takes the sunrise in the bright fortnight. Reversed in the dark fortnight.
SHUKLA_LUNAR_TITHIS = frozenset({1, 2, 3, 7, 8, 9, 13, 14, 15})


@dataclass(frozen=True)
class Config:
    swara_period: int = 60          # minutes per svara block (2.5 ghatikas)
    tattva_order: str = "classical"  # or "vayu_first"
    sushumna_sandhi: int = 4        # minutes total, centred on each svara change
    treat_akasha_as_sushumna: bool = False

    @property
    def order(self) -> list[str]:
        return TATTVA_ORDERS[self.tattva_order]


DEFAULT = Config()


def paksha_and_tithi(tithi_index: int) -> tuple[str, int]:
    """tithi_index is 0..29 (0 = Shukla Pratipada). -> ('shukla', 1..15)."""
    if not 0 <= tithi_index <= 29:
        raise ValueError(f"tithi_index must be 0..29, got {tithi_index}")
    paksha = "shukla" if tithi_index < 15 else "krishna"
    return paksha, (tithi_index % 15) + 1


def sunrise_svara(tithi_index: int) -> str:
    """Rule A. Which current must be flowing at sunrise today."""
    paksha, tithi = paksha_and_tithi(tithi_index)
    lunar = tithi in SHUKLA_LUNAR_TITHIS
    if paksha == "krishna":
        lunar = not lunar          # the dark fortnight reverses the rule
    return "ida" if lunar else "pingala"


def _scale(cfg: Config) -> float:
    """Tattva minutes are given for a 60-min block; rescale if period differs."""
    return cfg.swara_period / 60.0


def tattva_windows(cfg: Config = DEFAULT) -> list[tuple[str, float, float]]:
    """[(tattva_key, start_min, end_min)] within one svara block."""
    out, cursor, k = [], 0.0, _scale(cfg)
    for key in cfg.order:
        span = TATTVAS[key].minutes * k
        out.append((key, cursor, cursor + span))
        cursor += span
    return out


@dataclass
class State:
    at: datetime
    sunrise: datetime
    tithi_index: int
    svara: Svara                 # the current prescribed by Rule A + B
    tattva: Tattva
    sushumna: bool               # True during the sandhi window
    block: int                   # how many svara blocks since sunrise
    minutes_into_svara: float
    minutes_into_tattva: float
    next_tattva_change: datetime
    next_svara_change: datetime

    @property
    def effective_svara(self) -> Svara:
        return SVARAS["sushumna"] if self.sushumna else self.svara


def state_at(
    at: datetime,
    sunrise: datetime,
    tithi_index: int,
    cfg: Config = DEFAULT,
) -> State:
    """The prescribed current + element at `at`.

    `sunrise` must be the sunrise that OPENS the vedic day containing `at`
    (i.e. the most recent sunrise), and `tithi_index` the tithi at that sunrise.
    """
    elapsed = (at - sunrise).total_seconds() / 60.0
    if elapsed < 0:
        raise ValueError("sunrise must precede `at` — pass the previous sunrise")

    period = cfg.swara_period
    block = int(elapsed // period)
    into_svara = elapsed - block * period

    base = sunrise_svara(tithi_index)
    other = "pingala" if base == "ida" else "ida"
    svara_key = base if block % 2 == 0 else other

    tattva_key, t_start, t_end = None, 0.0, 0.0
    for key, s, e in tattva_windows(cfg):
        if s <= into_svara < e:
            tattva_key, t_start, t_end = key, s, e
            break
    if tattva_key is None:                      # float guard at the boundary
        tattva_key, t_start, t_end = cfg.order[-1], period - 1e-9, period

    svara_start = sunrise + timedelta(minutes=block * period)
    next_svara = svara_start + timedelta(minutes=period)
    next_tattva = svara_start + timedelta(minutes=t_end)

    half = cfg.sushumna_sandhi / 2.0
    in_sandhi = (into_svara < half) or (into_svara >= period - half)
    if cfg.treat_akasha_as_sushumna and tattva_key == "akasha":
        in_sandhi = True

    return State(
        at=at,
        sunrise=sunrise,
        tithi_index=tithi_index,
        svara=SVARAS[svara_key],
        tattva=TATTVAS[tattva_key],
        sushumna=in_sandhi,
        block=block,
        minutes_into_svara=into_svara,
        minutes_into_tattva=into_svara - t_start,
        next_tattva_change=next_tattva,
        next_svara_change=next_svara,
    )


@dataclass(frozen=True)
class Event:
    when: datetime
    kind: str            # svara | tattva | sushumna_open | sushumna_close
    svara: str
    tattva: str


def timeline(
    sunrise: datetime,
    tithi_index: int,
    start: datetime,
    end: datetime,
    cfg: Config = DEFAULT,
) -> list[Event]:
    """Every svara/tattva/sushumna transition in [start, end)."""
    events: list[Event] = []
    period = cfg.swara_period
    half = cfg.sushumna_sandhi / 2.0

    first = max(0, int(((start - sunrise).total_seconds() / 60.0) // period))
    last = int(((end - sunrise).total_seconds() / 60.0) // period) + 1

    for block in range(first, last + 1):
        block_start = sunrise + timedelta(minutes=block * period)
        for key, s, e in tattva_windows(cfg):
            t = block_start + timedelta(minutes=s)
            if not (start <= t < end):
                continue
            st = state_at(t + timedelta(seconds=1), sunrise, tithi_index, cfg)
            kind = "svara" if s == 0 else "tattva"
            events.append(Event(t, kind, st.svara.key, key))
        for offset, kind in ((-half, "sushumna_open"), (half, "sushumna_close")):
            t = block_start + timedelta(minutes=offset)
            if start <= t < end and t >= sunrise:
                events.append(Event(t, kind, "sushumna", "-"))

    return sorted(events, key=lambda e: (e.when, e.kind != "sushumna_open"))
