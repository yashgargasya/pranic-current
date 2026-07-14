"""The logbook — paired (prescribed, observed) records, and the statistics that
make them mean something.

Schema, one JSON object per line in events.jsonl:

  {
    "at":         "2026-07-13T20:02:00-07:00",   # the transition being judged
    "answered_at":"2026-07-13T20:04:11-07:00",   # when you actually tapped
    "lag_s":      131,                           # answer lag; big lag = weak obs
    "prescribed": "ida",                         # what the text says
    "observed":   "ida",                         # what you report
    "match":      true,
    "tattva":     "jala",
    "tithi":      13,                            # 0..29
    "paksha":     "krishna",
    "sushumna":   false,
    "block":      13                             # hours since sunrise
  }

Append-only. Never rewrite it — a logbook you can edit is not evidence.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from .swara import Config, paksha_and_tithi, state_at

LOG = Path("events.jsonl")


@dataclass
class Record:
    at: str
    answered_at: str
    lag_s: int
    prescribed: str
    observed: str
    match: bool
    tattva: str
    tithi: int
    paksha: str
    sushumna: bool
    block: int


def append(rec: Record, path: Path = LOG) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")


def load(path: Path = LOG) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out

def already_logged(at_iso: str, path: Path = LOG) -> bool:
    """A replayed tap must not double-count. Keyed on the transition, not the tap."""
    return any(r["at"] == at_iso for r in load(path))

# ---------- statistics ----------

def _prescribed_at(t: datetime, sunrise_of, cfg: Config) -> str:
    """Prescribed svara at an arbitrary time. `sunrise_of` is a cached lookup."""
    sr, ti = sunrise_of(t)
    return state_at(t, sr, ti, cfg).svara.key


def permutation_test(
    records: list[dict],
    sunrise_of,
    cfg: Config,
    n: int = 2000,
    max_shift_h: float = 12.0,
    seed: int = 0,
) -> dict:
    """Is the match rate better than phase-luck?

    The naive baseline (50%) is WRONG and will flatter you. The nasal cycle has
    its own endogenous period (~1.5-4 h); the prescribed series alternates on a
    fixed 60-min grid. Two periodic signals partially phase-lock by arithmetic
    alone, so a match rate well above 50% can arise from nothing.

    The honest null: shift the *clock* by a random offset, recompute what would
    have been prescribed at that shifted moment, and score your real observations
    against it. This destroys the phase relationship while preserving the
    autocorrelation of both series. Do it 2000 times; see where reality lands.
    """
    obs = [(datetime.fromisoformat(r["at"]), r["observed"])
           for r in records if r["observed"] in ("ida", "pingala")]
    if len(obs) < 30:
        return {"n": len(obs), "insufficient": True}

    real = sum(_prescribed_at(t, sunrise_of, cfg) == o for t, o in obs) / len(obs)

    rng = random.Random(seed)
    null = []
    for _ in range(n):
        shift = timedelta(hours=rng.uniform(0.5, max_shift_h))
        hits = sum(_prescribed_at(t + shift, sunrise_of, cfg) == o for t, o in obs)
        null.append(hits / len(obs))

    null.sort()
    beats = sum(1 for x in null if x >= real)
    return {
        "n": len(obs),
        "match_rate": real,
        "null_mean": sum(null) / len(null),
        "null_p05": null[int(0.05 * len(null))],
        "null_p95": null[int(0.95 * len(null))],
        "p_value": (beats + 1) / (n + 1),   # add-one: never report p=0
        "insufficient": False,
    }


def summarise(records: list[dict]) -> dict:
    """Descriptives. No inference here — that's what the permutation test is for."""
    scored = [r for r in records if r["observed"] in ("ida", "pingala")]
    out: dict = {
        "total": len(records),
        "scored": len(scored),
        "sushumna_reported": sum(1 for r in records if r["observed"] == "both"),
        "match_rate": (sum(r["match"] for r in scored) / len(scored)) if scored else 0.0,
        "median_lag_s": 0,
        "by_tattva": {},
        "by_paksha": {},
        "by_prescribed": {},
    }
    if scored:
        lags = sorted(r["lag_s"] for r in scored)
        out["median_lag_s"] = lags[len(lags) // 2]

    for field in ("tattva", "paksha", "prescribed"):
        buckets: dict[str, list[bool]] = {}
        for r in scored:
            buckets.setdefault(r[field], []).append(r["match"])
        out[f"by_{field}"] = {
            k: {"n": len(v), "rate": sum(v) / len(v)} for k, v in sorted(buckets.items())
        }
    return out


def make_record(at: datetime, answered_at: datetime, observed: str,
                sunrise: datetime, tithi_index: int, cfg: Config) -> Record:
    st = state_at(at, sunrise, tithi_index, cfg)
    paksha, _ = paksha_and_tithi(tithi_index)
    return Record(
        at=at.isoformat(),
        answered_at=answered_at.isoformat(),
        lag_s=int((answered_at - at).total_seconds()),
        prescribed=st.svara.key,
        observed=observed,
        match=(st.svara.key == observed),
        tattva=st.tattva.key,
        tithi=tithi_index,
        paksha=paksha,
        sushumna=st.sushumna,
        block=st.block,
    )
