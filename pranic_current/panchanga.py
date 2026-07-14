"""Pañcāṅga: sunrise/sunset + tithi, vāra, nakṣatra, yoga, karaṇa.

Swiss Ephemeris (`pyswisseph`) in Moshier mode — no ephemeris data files, so it
works fully offline. Sidereal quantities use Lahiri ayanāṁśa by default.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import swisseph as swe

FLAGS = swe.FLG_SWIEPH | swe.FLG_MOSEPH
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)

TITHIS = [
    "Pratipadā", "Dvitīyā", "Tṛtīyā", "Caturthī", "Pañcamī", "Ṣaṣṭhī",
    "Saptamī", "Aṣṭamī", "Navamī", "Daśamī", "Ekādaśī", "Dvādaśī",
    "Trayodaśī", "Caturdaśī", "Pūrṇimā/Amāvāsyā",
]
NAKSHATRAS = [
    "Aśvinī", "Bharaṇī", "Kṛttikā", "Rohiṇī", "Mṛgaśīrṣa", "Ārdrā", "Punarvasu",
    "Puṣya", "Āśleṣā", "Maghā", "Pūrva Phalgunī", "Uttara Phalgunī", "Hasta",
    "Citrā", "Svātī", "Viśākhā", "Anurādhā", "Jyeṣṭhā", "Mūla", "Pūrva Āṣāḍhā",
    "Uttara Āṣāḍhā", "Śravaṇa", "Dhaniṣṭhā", "Śatabhiṣā", "Pūrva Bhādrapadā",
    "Uttara Bhādrapadā", "Revatī",
]
YOGAS = [
    "Viṣkambha", "Prīti", "Āyuṣmān", "Saubhāgya", "Śobhana", "Atigaṇḍa",
    "Sukarma", "Dhṛti", "Śūla", "Gaṇḍa", "Vṛddhi", "Dhruva", "Vyāghāta",
    "Harṣaṇa", "Vajra", "Siddhi", "Vyatīpāta", "Varīyān", "Parigha", "Śiva",
    "Siddha", "Sādhya", "Śubha", "Śukla", "Brahma", "Indra", "Vaidhṛti",
]
MOVABLE_KARANAS = ["Bava", "Bālava", "Kaulava", "Taitila", "Gara", "Vaṇija", "Viṣṭi (Bhadrā)"]
VARAS = ["Ravivāra", "Somavāra", "Maṅgalavāra", "Budhavāra", "Guruvāra", "Śukravāra", "Śanivāra"]
RASHIS = [
    "Meṣa", "Vṛṣabha", "Mithuna", "Karka", "Siṁha", "Kanyā",
    "Tulā", "Vṛścika", "Dhanu", "Makara", "Kumbha", "Mīna",
]

NAK_ARC = 360 / 27          # 13°20′ per nakṣatra
PADA_ARC = NAK_ARC / 4      # 3°20′ per pada

PLANET_FLAGS = FLAGS | swe.FLG_SIDEREAL     # Lahiri sidereal longitudes

# (key, sanskrit, symbol, swe body). Ketu is derived from Rāhu (opposite point).
GRAHAS = [
    ("su", "Sūrya", "☉", swe.SUN),
    ("mo", "Candra", "☽", swe.MOON),
    ("ma", "Maṅgala", "♂", swe.MARS),
    ("bu", "Budha", "☿", swe.MERCURY),
    ("gu", "Guru", "♃", swe.JUPITER),
    ("sk", "Śukra", "♀", swe.VENUS),
    ("sa", "Śani", "♄", swe.SATURN),
    ("ra", "Rāhu", "☊", swe.MEAN_NODE),
    ("ke", "Ketu", "☋", None),
]


@dataclass(frozen=True)
class Place:
    name: str
    lat: float
    lon: float          # east positive
    tz: str
    alt: float = 0.0

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.tz)


# ---------- time helpers ----------

def to_jd(dt: datetime) -> float:
    u = dt.astimezone(timezone.utc)
    return swe.julday(u.year, u.month, u.day,
                      u.hour + u.minute / 60 + (u.second + u.microsecond / 1e6) / 3600)


def from_jd(jd: float, tz: ZoneInfo) -> datetime:
    y, m, d, h = swe.revjul(jd)
    base = datetime(y, m, d, tzinfo=timezone.utc)
    return (base + timedelta(hours=h)).astimezone(tz).replace(microsecond=0)


# ---------- longitudes ----------

def sun_moon(jd: float) -> tuple[float, float]:
    sun = swe.calc_ut(jd, swe.SUN, FLAGS)[0][0]
    moon = swe.calc_ut(jd, swe.MOON, FLAGS)[0][0]
    return sun % 360, moon % 360


def ayanamsa(jd: float) -> float:
    return swe.get_ayanamsa_ut(jd)


# ---------- navagraha ----------

@dataclass(frozen=True)
class Graha:
    key: str
    name: str
    symbol: str
    longitude: float        # sidereal degrees, 0..360
    rashi: str
    nakshatra: str
    pada: int               # 1..4
    navamsa: str            # D9 sign — the pada's rāśi in the navāṁśa varga
    retrograde: bool

    @property
    def position(self) -> tuple[str, str, int]:
        """The identity a transit watcher keys on."""
        return (self.rashi, self.nakshatra, self.pada)


def _place_graha(key: str, name: str, symbol: str, lon: float, retro: bool) -> Graha:
    lon %= 360
    return Graha(
        key=key, name=name, symbol=symbol, longitude=lon,
        rashi=RASHIS[int(lon // 30)],
        nakshatra=NAKSHATRAS[int(lon // NAK_ARC)],
        pada=int((lon % NAK_ARC) // PADA_ARC) + 1,
        navamsa=RASHIS[int(lon // PADA_ARC) % 12],   # 9 navāṁśas of 3°20′ per rāśi
        retrograde=retro,
    )


def graha_positions(jd: float) -> list[Graha]:
    """Sidereal (Lahiri) positions of the nine grahas at `jd`, in vāra-lord order."""
    out: list[Graha] = []
    rahu_lon = 0.0
    for key, name, symbol, body in GRAHAS:
        if key == "ke":                     # Ketu is 180° from Rāhu
            out.append(_place_graha(key, name, symbol, rahu_lon + 180, True))
            continue
        xx = swe.calc_ut(jd, body, PLANET_FLAGS)[0]
        lon, speed = xx[0] % 360, xx[3]
        retro = key == "ra" or speed < 0.0  # the mean node always runs backwards
        if key == "ra":
            rahu_lon = lon
        out.append(_place_graha(key, name, symbol, lon, retro))
    return out


# ---------- rise / set ----------

def _rise_trans(jd_start: float, place: Place, rising: bool) -> float:
    rsmi = (swe.CALC_RISE if rising else swe.CALC_SET) | swe.BIT_HINDU_RISING
    geo = (place.lon, place.lat, place.alt)
    try:                                    # pyswisseph >= 2.08
        res = swe.rise_trans(jd_start, swe.SUN, rsmi, geo, 0.0, 0.0, FLAGS)
    except TypeError:                       # older signature
        res = swe.rise_trans(jd_start, swe.SUN, b"", FLAGS, rsmi, geo, 0.0, 0.0)
    tret = res[1]
    return tret[0]


def sunrise(day: datetime, place: Place) -> datetime:
    """First sunrise at or after local midnight of `day`."""
    local_midnight = day.astimezone(place.zone).replace(
        hour=0, minute=0, second=0, microsecond=0)
    return from_jd(_rise_trans(to_jd(local_midnight), place, True), place.zone)


def sunset(day: datetime, place: Place) -> datetime:
    local_midnight = day.astimezone(place.zone).replace(
        hour=0, minute=0, second=0, microsecond=0)
    return from_jd(_rise_trans(to_jd(local_midnight), place, False), place.zone)


def vedic_day_sunrise(at: datetime, place: Place) -> datetime:
    """The sunrise that OPENS the vedic day containing `at` (day = sunrise→sunrise)."""
    sr = sunrise(at, place)
    if at < sr:
        sr = sunrise(at - timedelta(days=1), place)
    return sr


# ---------- the five limbs ----------

def tithi_index(jd: float) -> int:
    """0..29 — 0 is Śukla Pratipadā."""
    sun, moon = sun_moon(jd)
    return int(((moon - sun) % 360) // 12)


def _end_of(jd: float, value_fn, arc: float, tz: ZoneInfo) -> datetime:
    """Bisect for the moment the running angle next crosses a multiple of `arc`."""
    start = value_fn(jd)
    target = (int(start // arc) + 1) * arc
    lo, hi = jd, jd + 2.0
    for _ in range(60):
        mid = (lo + hi) / 2
        v = value_fn(mid)
        if v < start:                       # wrapped past 360
            v += 360
        if v < target:
            lo = mid
        else:
            hi = mid
    return from_jd(hi, tz)


def _start_of(jd: float, value_fn, arc: float, tz: ZoneInfo) -> datetime:
    """Bisect backward for the moment the running angle last crossed a multiple
    of `arc` — i.e. when the current tithi/nakṣatra/etc. began."""
    start = value_fn(jd)
    target = int(start // arc) * arc        # boundary at or just below `start`
    lo, hi = jd - 2.0, jd
    for _ in range(60):
        mid = (lo + hi) / 2
        v = value_fn(mid)
        if v > start:                       # wrapped back past 0
            v -= 360
        if v < target:
            lo = mid
        else:
            hi = mid
    return from_jd(hi, tz)


@dataclass
class Panchanga:
    date: datetime
    place: Place
    sunrise: datetime
    sunset: datetime
    vara: str
    tithi_index: int
    tithi_name: str
    paksha: str
    tithi_begins: datetime
    tithi_ends: datetime
    nakshatra: str
    nakshatra_begins: datetime
    nakshatra_ends: datetime
    yoga: str
    yoga_begins: datetime
    yoga_ends: datetime
    karana: str
    karana_begins: datetime
    karana_ends: datetime
    moon_phase_pct: float
    planets: list[Graha]

    def _fmt(self, d: datetime) -> str:
        """HH:MM, prefixed with the weekday when it falls outside sunrise's day."""
        return (d.strftime("%H:%M") if d.date() == self.sunrise.date()
                else d.strftime("%a %H:%M"))

    def as_lines(self) -> list[str]:
        span = lambda b, e: f"{self._fmt(b)}→{self._fmt(e)}"
        return [
            f"☉ Sunrise {self._fmt(self.sunrise)} · Sunset {self._fmt(self.sunset)}",
            f"📅 {self.vara} · {self.paksha.capitalize()} {self.tithi_name} "
            f"({span(self.tithi_begins, self.tithi_ends)})",
            f"⭐ Nakṣatra {self.nakshatra} ({span(self.nakshatra_begins, self.nakshatra_ends)})",
            f"🧿 Yoga {self.yoga} ({span(self.yoga_begins, self.yoga_ends)})",
            f"🔀 Karaṇa {self.karana} ({span(self.karana_begins, self.karana_ends)})",
            f"🌘 Moon {self.moon_phase_pct:.0f}% illuminated",
        ]

    def sky_lines(self) -> list[str]:
        """The navagraha snapshot — one line per planet."""
        out = ["<b>Sky at sunrise</b>  <i>nakṣatra pada [navāṁśa] · rāśi</i>"]
        for g in self.planets:
            retro = " ℞" if g.retrograde else ""
            out.append(f"{g.symbol} {g.name} — {g.nakshatra} {g.pada} "
                       f"[{g.navamsa}] · {g.rashi}{retro}")
        return out


def compute(at: datetime, place: Place) -> Panchanga:
    """Pañcāṅga reckoned at the sunrise of the vedic day containing `at`."""
    sr = vedic_day_sunrise(at, place)
    ss = sunset(sr, place)
    jd = to_jd(sr)
    tz = place.zone
    sun, moon = sun_moon(jd)

    ti = tithi_index(jd)
    paksha = "śukla" if ti < 15 else "kṛṣṇa"
    tname = TITHIS[ti % 15]
    if ti % 15 == 14:
        tname = "Pūrṇimā" if ti < 15 else "Amāvāsyā"

    diff = lambda j: ((lambda s, m: (m - s) % 360)(*sun_moon(j)))
    moon_sid = lambda j: (sun_moon(j)[1] - ayanamsa(j)) % 360
    yoga_sid = lambda j: (sum(sun_moon(j)) - 2 * ayanamsa(j)) % 360

    nak = int(moon_sid(jd) // (360 / 27))
    yg = int(yoga_sid(jd) // (360 / 27))

    k = int(diff(jd) // 6)                  # 0..59
    if k == 0:
        karana = "Kiṁstughna"
    elif k >= 57:
        karana = ["Śakuni", "Catuṣpada", "Nāga"][k - 57]
    else:
        karana = MOVABLE_KARANAS[(k - 1) % 7]

    return Panchanga(
        date=sr, place=place, sunrise=sr, sunset=ss,
        vara=VARAS[(sr.weekday() + 1) % 7],
        tithi_index=ti, tithi_name=tname, paksha=paksha,
        tithi_begins=_start_of(jd, diff, 12.0, tz),
        tithi_ends=_end_of(jd, diff, 12.0, tz),
        nakshatra=NAKSHATRAS[nak],
        nakshatra_begins=_start_of(jd, moon_sid, NAK_ARC, tz),
        nakshatra_ends=_end_of(jd, moon_sid, NAK_ARC, tz),
        yoga=YOGAS[yg],
        yoga_begins=_start_of(jd, yoga_sid, NAK_ARC, tz),
        yoga_ends=_end_of(jd, yoga_sid, NAK_ARC, tz),
        karana=karana,
        karana_begins=_start_of(jd, diff, 6.0, tz),
        karana_ends=_end_of(jd, diff, 6.0, tz),
        moon_phase_pct=(1 - __import__("math").cos(__import__("math").radians(diff(jd)))) / 2 * 100,
        planets=graha_positions(jd),
    )
