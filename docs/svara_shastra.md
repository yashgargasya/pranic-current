# Svara Śāstra — the rule-set encoded in this project

Source tradition: **Śiva Svarodaya** (a Śiva–Pārvatī saṁvāda of ~395 verses, transmitted within the
Śaiva/Nātha tantric stream), together with its standard commentarial reading (Svara Yoga).

> **On verse numbers:** manuscript recensions differ, and verse numbering is not stable across
> editions. Below I cite *approximate* verse ranges and paraphrase the content rather than quoting
> any modern translator. Where traditions genuinely disagree, the disagreement is marked
> **[variant]** and exposed as a config knob rather than silently decided.

---

## 1. The three currents (svara / nāḍī)

| Current | Nostril | Deity/luminary | Guṇa | Nature | Polarity |
|---|---|---|---|---|---|
| **Iḍā** (candra svara) | Left | Moon | tamas→sattva, cooling | soft, moist, receptive, nourishing | negative / "female" |
| **Piṅgalā** (sūrya svara) | Right | Sun | rajas, heating | sharp, dry, projective, consuming | positive / "male" |
| **Suṣumṇā** | Both equally, or neither clearly | Fire of time / Rudra | sattva / transcendent | still, void, no worldly traction | neutral |

The text's basic axiom: *prāṇa moves; the direction of its movement is legible at the nostrils; and
action taken with the current succeeds while action taken against it fails.* Suṣumṇā is called
**viṣa-nāḍī** ("poison channel") for worldly action and simultaneously the only doorway for yoga,
meditation, mantra, and mokṣa. Nothing external should be begun in it.

---

## 2. Which current *should* be flowing, and when

Two rules stack.

### Rule A — the sunrise svara (tithi/pakṣa rule)

The svara that must be flowing **at sunrise** is fixed by the lunar fortnight and the tithi:

| Tithi (within its pakṣa) | Śukla pakṣa (waxing) | Kṛṣṇa pakṣa (waning) |
|---|---|---|
| 1, 2, 3 · 7, 8, 9 · 13, 14, 15 | **Iḍā** (left / lunar) | **Piṅgalā** (right / solar) |
| 4, 5, 6 · 10, 11, 12 | **Piṅgalā** (right / solar) | **Iḍā** (left / lunar) |

(Śukla-15 = Pūrṇimā; Kṛṣṇa-15 = Amāvāsyā.) The "day" here is the **vedic day: sunrise to sunrise**,
not midnight to midnight. The tithi used is the one *current at that sunrise*.

### Rule B — the alternation

From sunrise onward the svara alternates continuously, **every 2½ ghaṭikās = 60 minutes**, through
the day *and* the night, until the next sunrise re-anchors it by Rule A.

> **[variant]** Some lineages take the alternation as ~1 hour, some as 1 hour 30 min, some hold the
> sunrise svara for the whole day on the "three-day" sets. This project defaults to 60 min and
> exposes `swara_period_minutes`.

### Rule C — suṣumṇā

Suṣumṇā appears in the **sandhi** (junction): the few minutes in which one svara is dying and the
other is not yet born, i.e. straddling every hourly change — and pre-eminently at the sandhyās
(sunrise, sunset), at the pakṣa turn (Pūrṇimā/Amāvāsyā), and whenever it arrives unbidden. It is
also functionally present in the **ākāśa tattva** at the tail of every hour.

Diagnostic: both nostrils flow equally, or the flow feels erratic/absent; the mind is either
unusually still or unusually scattered. Traditional counsel: *do nothing outward. Sit.*

### Rule D — svara *out of order* is the prognostic signal

The text's real diagnostic weight is here. If the wrong svara flows at sunrise, or one svara flows
continuously for many hours/days, or suṣumṇā persists, it is read as disorder — of the body, of the
plan, or of the timeline. The engine therefore reports **prescribed** current; you observe your
**actual** one; the *gap between them* is the reading.

---

## 3. The five tattvas inside each current

Every 60-minute svara block is subdivided; the five elements rise in sequence and the whole set is
exhausted before the svara turns:

| Order | Tattva | Duration |
|---|---|---|
| 1 | Pṛthvī (earth) | 20 min |
| 2 | Jala / Āpas (water) | 16 min |
| 3 | Agni / Tejas (fire) | 12 min |
| 4 | Vāyu (air) | 8 min |
| 5 | Ākāśa (ether) | 4 min |
| | **total** | **60 min** |

> **[variant]** A second stream orders them **vāyu → agni → pṛthvī → jala → ākāśa**. Both are
> attested. Config: `tattva_order`.

So a full lunar+solar cycle = 2 hours = 10 tattva windows. Roughly **120 tattva changes and 24 svara
changes per day** — which is why the notifier defaults to *svara-only* alerts, with tattva alerts
opt-in.

---

## 4. How to identify what is running — the fourfold test

Hold the back of a clean hand, or a **cold mirror**, under the nostrils and exhale. Read four things:

### 4.1 Which current

- **Feel**: block one nostril, breathe; compare volume, temperature, ease. The dominant side is
  the flowing svara. Left = cool stream; right = warm stream.
- Iḍā feels *cool, slow, wide, smooth*; Piṅgalā feels *warm, quick, narrow, forceful*.
- Suṣumṇā: equal, or "neither" — often felt as a strange suspension.

### 4.2 Which tattva — colour, shape, direction, length

| Tattva | Colour | Mirror-mark / yantra | Direction of exhaled flow (at the nostril) | Length of exhalation | Bīja | Taste | Felt quality |
|---|---|---|---|---|---|---|---|
| **Pṛthvī** (earth) | yellow / golden | **square** | straight out, **middle** | **12 aṅgula** | LAṀ | sweet | heavy, steady, grounded, slightly dull; contentment |
| **Jala** (water) | white / silver | **crescent** (half-moon) | **downward** | **16 aṅgula** (longest) | VAṀ | astringent / saline | cool, fluid, moist, mobile; ease and flow |
| **Agni** (fire) | red | **triangle** (upward) | **upward** | **4 aṅgula** (shortest) | RAṀ | pungent / bitter-hot | hot, sharp, restless, hungry; irritability |
| **Vāyu** (air) | blue / smoke-grey / green | **hexagon or circle** | **oblique / sideways** (slanting) | **8 aṅgula** | YAṀ | sour | light, dry, erratic, cold-mobile; anxiety, motion |
| **Ākāśa** (ether) | black / transparent, speckled with many colours | **dots / bindu**, no form | **diffuse, all directions**; no clear stream | no fixed length | HAṀ | bitter | void, spacious, empty; neither hunger nor drive |

An aṅgula is a finger-breadth (~1.9 cm); measure where the breath ceases to be felt on the back of
the hand held before the nose.

### 4.3 Direction (dik) — the applied rule

Sit or set out with the flowing svara **on the side of your advantage**: face/step so that the
active nostril's side leads. Classical shorthand — leave the house with the foot on the same side as
the flowing svara; keep the flowing side toward the object of the meeting; keep the empty side
toward the opponent.

### 4.4 What each is *for*

| | Favours | Avoid |
|---|---|---|
| **Iḍā** | anything meant to *last* or to *soften*: beginning long journeys, entering a house, planting, marriage, alms, medicine, study, reconciliation, sleep, sādhanā | violent/harsh effort, confrontation |
| **Piṅgalā** | anything *hot, hard, brief*: eating, digesting, bathing, physical labour, debate, competition, sex, difficult or destructive tasks | initiating anything meant to endure |
| **Suṣumṇā** | meditation, mantra, prāṇāyāma, kuṇḍalinī, contemplation of death, mokṣa | *all* worldly action — "fruitless or ruinous" |
| **Pṛthvī** | foundations, property, long-term commitments, stable gains | speed |
| **Jala** | most auspicious for general undertakings; water, creativity, negotiation, travel | destructive acts |
| **Agni** | cruel/urgent acts, breaking, contests, forcing | new ventures, healing, marriage |
| **Vāyu** | motion, transport, transient business, expulsion | anything requiring permanence — results scatter |
| **Ākāśa** | *only* meditation | everything else — held to be barren |

---

## 5. Honest framing

This is a contemplative-diagnostic system from a tantric lineage, encoded here faithfully. The
prescribed table is what the *text* says should be flowing; it is not a claim about physiology. The
nasal cycle itself is a real, measured phenomenon (alternating turbinate congestion, roughly
1.5–4 hours, coupled to autonomic tone) — but it does not track the tithi. Treat the mismatch
between prescribed and observed as material for practice and self-observation, not as medicine.
