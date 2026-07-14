"""Prāṇic Current — CLI and daemon.

  python -m pranic_current now          # what should be flowing right now
  python -m pranic_current today        # full timeline for the vedic day
  python -m pranic_current digest       # send the sunrise panchanga digest
  python -m pranic_current run          # the notifier daemon
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from . import panchanga as pc
from .notify import Telegram, digest_message, transition_message
from .swara import Config, state_at, sunrise_svara, timeline
from .tattva import SVARAS, TATTVAS

log = logging.getLogger("pranic")

DEFAULT_CONFIG = {
    "place": {"name": "San Leandro, CA", "lat": 37.7249, "lon": -122.1561,
              "tz": "America/Los_Angeles"},
    "rules": {"swara_period": 60, "tattva_order": "classical",
              "sushumna_sandhi": 4, "treat_akasha_as_sushumna": False},
    "notify": {
        "swara_changes": True,
        "tattva_changes": False,
        "sushumna": True,
        "sunrise_digest": True,
        "quiet_hours": [22, 6],       # inclusive start, exclusive end (local)
        "quiet_allows_sushumna": False,
    },
    "telegram": {"token": "${TELEGRAM_BOT_TOKEN}", "chat_id": "${TELEGRAM_CHAT_ID}"},
}


def load_config(path: str | None) -> dict:
    try:                                  # optional; VS Code launch.json also injects .env
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    cfg = DEFAULT_CONFIG
    if path and Path(path).exists():
        loaded = yaml.safe_load(Path(path).read_text()) or {}
        for k, v in loaded.items():
            cfg[k] = {**cfg.get(k, {}), **v} if isinstance(v, dict) else v
    t = cfg["telegram"]
    for k in ("token", "chat_id"):
        v = str(t.get(k, ""))
        if v.startswith("${") and v.endswith("}"):
            t[k] = os.environ.get(v[2:-1], "")
    return cfg


def build(cfg: dict) -> tuple[pc.Place, Config]:
    p = cfg["place"]
    return (
        pc.Place(name=p["name"], lat=float(p["lat"]), lon=float(p["lon"]), tz=p["tz"]),
        Config(**cfg["rules"]),
    )


def _quiet(now: datetime, cfg: dict) -> bool:
    start, end = cfg["notify"]["quiet_hours"]
    h = now.hour
    return (start <= h or h < end) if start > end else (start <= h < end)


# ---------- commands ----------

def cmd_now(cfg: dict) -> None:
    place, rules = build(cfg)
    now = datetime.now(place.zone)
    pan = pc.compute(now, place)
    st = state_at(now, pan.sunrise, pan.tithi_index, rules)

    print(f"\n{now:%Y-%m-%d %H:%M}  ·  {place.name}\n")
    for line in pan.as_lines():
        print(" ", line)
    print()
    eff = st.effective_svara
    print(f"  Prescribed current : {eff.emoji} {eff.sanskrit}  ({eff.nostril})")
    if st.sushumna:
        print(f"  (sandhi — {st.svara.sanskrit} is the underlying current)")
    print(f"  Element            : {st.tattva.emoji} {st.tattva.sanskrit} "
          f"({st.tattva.english})")
    print(f"    colour {st.tattva.colour} · {st.tattva.yantra} · "
          f"flows {st.tattva.direction} · {st.tattva.angula}")
    print(f"    feel: {st.tattva.feel}")
    print(f"\n  → element turns {st.next_tattva_change:%H:%M}, "
          f"current turns {st.next_svara_change:%H:%M}\n")


def cmd_today(cfg: dict) -> None:
    place, rules = build(cfg)
    now = datetime.now(place.zone)
    pan = pc.compute(now, place)
    end = pan.sunrise + timedelta(days=1)
    print(f"\n  {pan.sunrise:%a %d %b} sunrise {pan.sunrise:%H:%M} → "
          f"{end:%H:%M} · {place.name}")
    print(f"  {pan.paksha} {pan.tithi_name} · sunrise current: "
          f"{SVARAS[sunrise_svara(pan.tithi_index)].english}\n")
    for e in timeline(pan.sunrise, pan.tithi_index, pan.sunrise, end, rules):
        if e.kind == "svara":
            s = SVARAS[e.svara]
            print(f"  {e.when:%H:%M}  ══ {s.emoji} {s.english.upper()} "
                  f"({s.nostril}) ══")
        elif e.kind == "tattva":
            t = TATTVAS[e.tattva]
            print(f"  {e.when:%H:%M}      {t.emoji} {t.sanskrit:<12} {t.english}")
    print()


def cmd_digest(cfg: dict, dry: bool) -> None:
    place, rules = build(cfg)
    tg = Telegram(cfg["telegram"]["token"], cfg["telegram"]["chat_id"], dry)
    now = datetime.now(place.zone)
    pan = pc.compute(now, place)
    st = state_at(now, pan.sunrise, pan.tithi_index, rules)
    events = timeline(pan.sunrise, pan.tithi_index, pan.sunrise,
                      pan.sunrise + timedelta(days=1), rules)
    tg.send(digest_message(pan, st, events))


def cmd_run(cfg: dict, dry: bool, interval: int) -> None:
    """Poll; fire on every change of the (svara, tattva, sushumna) tuple."""
    place, rules = build(cfg)
    n = cfg["notify"]
    tg = Telegram(cfg["telegram"]["token"], cfg["telegram"]["chat_id"], dry)

    last_key = None
    last_digest_date = None
    log.info("watching %s · period=%dmin · order=%s",
             place.name, rules.swara_period, rules.tattva_order)

    while True:
        try:
            now = datetime.now(place.zone)
            pan = pc.compute(now, place)
            st = state_at(now, pan.sunrise, pan.tithi_index, rules)
            key = (st.svara.key, st.tattva.key, st.sushumna)

            if n["sunrise_digest"] and last_digest_date != pan.sunrise.date() \
                    and now >= pan.sunrise:
                events = timeline(pan.sunrise, pan.tithi_index, pan.sunrise,
                                  pan.sunrise + timedelta(days=1), rules)
                tg.send(digest_message(pan, st, events))
                last_digest_date = pan.sunrise.date()

            if last_key is None:
                last_key = key                      # don't fire on cold start
            elif key != last_key:
                prev_svara, _, prev_sush = last_key
                if st.sushumna and not prev_sush:
                    kind = "sushumna_open"
                elif st.svara.key != prev_svara:
                    kind = "svara"
                elif st.tattva.key != last_key[1]:
                    kind = "tattva"
                else:
                    kind = None                     # sushumna just closed

                want = (
                    (kind == "svara" and n["swara_changes"])
                    or (kind == "tattva" and n["tattva_changes"])
                    or (kind == "sushumna_open" and n["sushumna"])
                )
                muted = _quiet(now, cfg) and not (
                    kind == "sushumna_open" and n["quiet_allows_sushumna"])
                if want and not muted:
                    tg.send(transition_message(st, kind))
                last_key = key

        except Exception:                            # never let the daemon die
            log.exception("cycle failed; retrying")
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pranic_current")
    ap.add_argument("command", choices=["now", "today", "digest", "run"])
    ap.add_argument("-c", "--config", default="config.yaml")
    ap.add_argument("--dry-run", action="store_true",
                    help="print messages instead of sending")
    ap.add_argument("--interval", type=int, default=20, help="poll seconds")
    a = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(a.config)

    if a.command == "now":
        cmd_now(cfg)
    elif a.command == "today":
        cmd_today(cfg)
    elif a.command == "digest":
        cmd_digest(cfg, a.dry_run)
    else:
        cmd_run(cfg, a.dry_run, a.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
