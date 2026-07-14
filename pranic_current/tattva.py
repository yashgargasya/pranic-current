"""Reference data for the three svaras and five tattvas (Shiva Svarodaya)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Svara:
    key: str
    sanskrit: str
    english: str
    nostril: str
    emoji: str
    feel: str
    favours: str
    avoid: str


IDA = Svara(
    key="ida",
    sanskrit="Iḍā / candra svara",
    english="Lunar current",
    nostril="left",
    emoji="🌙",
    feel="cool, slow, wide, smooth; mind receptive and settled",
    favours="lasting or gentle work — journeys, moving in, planting, marriage, "
    "alms, medicine, study, reconciliation, sādhanā, sleep",
    avoid="harsh effort, confrontation, forcing",
)

PINGALA = Svara(
    key="pingala",
    sanskrit="Piṅgalā / sūrya svara",
    english="Solar current",
    nostril="right",
    emoji="☀️",
    feel="warm, quick, narrow, forceful; mind active and outward",
    favours="hot, hard, short work — eating, bathing, labour, debate, contest, "
    "sex, difficult or destructive tasks",
    avoid="beginning anything meant to endure",
)

SUSHUMNA = Svara(
    key="sushumna",
    sanskrit="Suṣumṇā",
    english="Central current",
    nostril="both / neither",
    emoji="🕉️",
    feel="both nostrils equal, or flow suspended; stillness or scattering",
    favours="meditation, mantra, prāṇāyāma, kuṇḍalinī, contemplation — nothing else",
    avoid="ALL worldly action (viṣa-nāḍī — 'poison channel')",
)

SVARAS = {s.key: s for s in (IDA, PINGALA, SUSHUMNA)}


@dataclass(frozen=True)
class Tattva:
    key: str
    sanskrit: str
    english: str
    minutes: int
    emoji: str
    colour: str
    hex: str
    yantra: str          # mark left on a cold mirror
    direction: str       # direction the exhaled stream leaves the nostril
    angula: str          # length of exhalation, finger-breadths
    bija: str
    taste: str
    feel: str
    favours: str
    avoid: str


PRITHVI = Tattva(
    key="prithvi", sanskrit="Pṛthvī", english="Earth", minutes=20, emoji="🟨",
    colour="yellow / golden", hex="#E3B505", yantra="square",
    direction="straight out through the middle", angula="12 aṅgula",
    bija="LAṀ", taste="sweet",
    feel="heavy, steady, grounded, a little dull; contentment",
    favours="foundations, property, long commitments, stable gain",
    avoid="anything needing speed",
)

JALA = Tattva(
    key="jala", sanskrit="Jala / Āpas", english="Water", minutes=16, emoji="⬜",
    colour="white / silver", hex="#DCE6F0", yantra="crescent (half-moon)",
    direction="downward", angula="16 aṅgula (longest)",
    bija="VAṀ", taste="astringent / saline",
    feel="cool, fluid, moist, mobile; ease and flow",
    favours="most auspicious generally — negotiation, creativity, water, travel",
    avoid="destructive acts",
)

AGNI = Tattva(
    key="agni", sanskrit="Agni / Tejas", english="Fire", minutes=12, emoji="🔺",
    colour="red", hex="#C1272D", yantra="upward triangle",
    direction="upward", angula="4 aṅgula (shortest)",
    bija="RAṀ", taste="pungent, hot",
    feel="hot, sharp, restless, hungry; irritability",
    favours="urgent, cruel or breaking acts; contests; forcing an issue",
    avoid="new ventures, healing, marriage",
)

VAYU = Tattva(
    key="vayu", sanskrit="Vāyu", english="Air", minutes=8, emoji="🔵",
    colour="blue / smoke-grey / green", hex="#4A6D7C", yantra="hexagon or circle",
    direction="oblique — slanting off to the side", angula="8 aṅgula",
    bija="YAṀ", taste="sour",
    feel="light, dry, erratic, cold and mobile; anxiety, restlessness",
    favours="motion, transport, transient business, expulsion",
    avoid="anything meant to last — results scatter",
)

AKASHA = Tattva(
    key="akasha", sanskrit="Ākāśa", english="Ether", minutes=4, emoji="⚫",
    colour="black / transparent, speckled with many colours", hex="#2B2B33",
    yantra="dots / bindu — no form",
    direction="diffuse, in all directions; no clear stream",
    angula="no fixed length", bija="HAṀ", taste="bitter",
    feel="void, spacious, empty; neither hunger nor drive",
    favours="meditation only — held to be a doorway, near-suṣumṇā",
    avoid="every worldly undertaking — barren of fruit",
)

TATTVAS = {t.key: t for t in (PRITHVI, JALA, AGNI, VAYU, AKASHA)}

# Two attested sequences. See docs/svara_shastra.md §3 [variant].
TATTVA_ORDERS: dict[str, list[str]] = {
    "classical": ["prithvi", "jala", "agni", "vayu", "akasha"],
    "vayu_first": ["vayu", "agni", "prithvi", "jala", "akasha"],
}
