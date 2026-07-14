# Prāṇic Current — Roadmap

**North star.** Determine whether the body's *actual* prāṇic current (which nostril /
which tattva is truly flowing) tracks the *textual* prescription of the Śiva Svarodaya —
and how that agreement shifts across environments. Every phase below exists to collect
cleaner body data and to sharpen that comparison.

The work is staged deliberately: we only add a heavier data-capture burden once the
lighter one is habitual and the analysis for it is in place. "As we get more body data,
we unlock the next phase."

---

## Phase 0 — Textual engine + minimal capture  *(done)*

- Svara/tattva engine from sunrise + tithi (`swara.py`), fully unit-tested.
- Pañcāṅga at sunrise: tithi, vāra, nakṣatra, yoga, karaṇa, moon phase (`panchanga.py`).
- Sunrise digest (once/day) + one-by-one svara-change pushes.
- **Body capture v1:** at each channel change (Iḍā↔Piṅgalā), a Left/Right/Both poll;
  logged to `events.jsonl`; scored against prescription; permutation test in `pranic stats`.
- Single-instance daemon lock; background start/stop scripts.

## Phase 1 — Full sky at sunrise + transit alerts  *(next)*

Goal: the sunrise digest should tell you how the whole sky looks for the day, and the
daemon should ping you when the sky meaningfully changes.

1. **Begin + end for all five limbs.** Show start *and* end of the running tithi,
   nakṣatra, yoga, and karaṇa (add a `_start_of` bisection to mirror `_end_of`; give
   karaṇa its own end).
2. **Navagraha snapshot.** Compute sidereal longitude of Sun, Moon, Mars, Mercury,
   Jupiter, Venus, Saturn, Rāhu, Ketu → **Rāśi (12), Nakṣatra (27), Pada (4)** + retrograde
   flag. Add a "Sky at sunrise" block to the digest.
3. **Transit notifications.** Daemon watches each planet's (rāśi, nakṣatra, pada) tuple
   and pushes on change. Volume policy TBD (Moon changes pada ~4×/day and nakṣatra ~daily;
   outer planets change over weeks/months) — likely: Moon = nakṣatra-level, others =
   pada-level, all rāśi ingresses always. Respect quiet hours.

## Phase 2 — Full prāṇic-current push

- Enable **nadi + tattva** pushes: e.g. "Lunar · Earth", then "Lunar · Water", … each with
  a short blurb — what to expect in the body, what activity the period favours/avoids.
- Content already exists in `tattva.py`/`notify.transition_message`; needs the config flip,
  a tighter body-and-activity blurb, and quiet-hours respect (this is ~120 pushes/day, so
  make the cadence configurable).

## Phase 3 — Richer body capture: the tattva poll

*Unlocks once Phase-2 tattva awareness is habitual and we can distinguish tattvas in the breath.*

- At each tattva change, poll the **observed tattva** (mirror-mark, exhale direction/length,
  taste, felt quality), not just the nostril.
- Extend the logbook schema with `observed_tattva`; extend scoring/stats to the tattva grid.

## Phase 4 — Environmental study

*Unlocks once we have a solid baseline of nostril + tattva observations.*

- Tag each observation with **environment**: temperature (cold/hot), setting
  (indoor/outdoor), and stress (low/high) — and any others that prove informative.
- Study where body prāṇa follows vs. diverges from the textual current *as a function of
  environment* — i.e., under what conditions the prescription holds.

## Phase 5 — Analysis & sync score

- Extend `pranic stats` / the permutation test across all dimensions: nostril, tattva,
  planetary context, environment.
- Produce a standing **"sync score"**: how well body prāṇa matches the text, sliced by
  condition, with an honest phase-shifted null.

---

### Design constraints carried throughout
- **Message volume is a first-class concern.** Every new push type is opt-in / cadence-
  configurable and respects quiet hours. (We already fought duplicate/oversized messages.)
- **The logbook is append-only evidence** — never rewritten.
- **Engine stays ephemeris-free where it can** so the ritual rules test independently of
  the astronomy.
