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
    tithi_ends: datetime
    nakshatra: str
    nakshatra_ends: datetime
    yoga: str
    yoga_ends: datetime
    karana: str
    moon_phase_pct: float

    def as_lines(self) -> list[str]:
        f = lambda d: d.strftime("%H:%M")
        return [
            f"☉ Sunrise {f(self.sunrise)} · Sunset {f(self.sunset)}",
            f"📅 {self.vara} · {self.paksha.capitalize()} {self.tithi_name} "
            f"(→ {f(self.tithi_ends)})",
            f"⭐ Nakṣatra {self.nakshatra} (→ {f(self.nakshatra_ends)})",
            f"🧿 Yoga {self.yoga} (→ {f(self.yoga_ends)}) · Karaṇa {self.karana}",
            f"🌘 Moon {self.moon_phase_pct:.0f}% illuminated",
        ]


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
        tithi_ends=_end_of(jd, diff, 12.0, tz),
        nakshatra=NAKSHATRAS[nak],
        nakshatra_ends=_end_of(jd, moon_sid, 360 / 27, tz),
        yoga=YOGAS[yg],
        yoga_ends=_end_of(jd, yoga_sid, 360 / 27, tz),
        karana=karana,
        moon_phase_pct=(1 - __import__("math").cos(__import__("math").radians(diff(jd)))) / 2 * 100,
    )
