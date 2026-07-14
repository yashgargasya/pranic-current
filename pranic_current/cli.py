"""Prāṇic Current — CLI and daemon.

  pranic now       what should be flowing right now
  pranic today     the full timeline for the vedic day
  pranic test      send a test Telegram, verify the token and buttons
  pranic digest    send the sunrise panchanga digest
  pranic run       the notifier daemon — sends, and captures your taps
  pranic stats     what the logbook says, against an honest null
"""

from __future__ import annotations

import argparse
import functools
import logging
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

if sys.platform == "win32":            # cp1252 chokes on ā, ṭ, ś
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import time  # noqa: E402

from . import logbook as lb  # noqa: E402
from . import panchanga as pc  # noqa: E402
from .notify import (Telegram, digest_message, test_message,  # noqa: E402
                     transit_message, transition_message)
from .swara import Config, state_at, sunrise_svara, timeline  # noqa: E402
from .tattva import SVARAS, TATTVAS  # noqa: E402

log = logging.getLogger("pranic")

DEFAULT_CONFIG = {
    "place": {"name": "Union City, CA", "lat": 37.5934, "lon": -122.0439,
              "tz": "America/Los_Angeles"},
    "rules": {"swara_period": 60, "tattva_order": "classical",
              "sushumna_sandhi": 4, "treat_akasha_as_sushumna": False},
    "notify": {
        "swara_changes": True,
        "tattva_changes": False,
        "sushumna": True,
        "sunrise_digest": True,
        "ask_observation": True,       # attach the left/right/both buttons
        "transits": False,             # planet rāśi/nakṣatra/pada changes
        "quiet_hours": [22, 6],
        "quiet_allows_sushumna": False,
        "quiet_allows_transits": False,
    },
    "telegram": {"token": "${TELEGRAM_BOT_TOKEN}", "chat_id": "${TELEGRAM_CHAT_ID}"},
}


def load_config(path: str | None) -> dict:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    cfg = DEFAULT_CONFIG
    if path and Path(path).exists():
        loaded = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
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


def _acquire_singleton(path: Path):
    """Hold an exclusive OS lock for the daemon's whole lifetime, so a second
    `pranic run` in the same directory can't start and fire duplicate messages.

    The kernel drops the lock automatically when this process exits or is killed,
    so there is no stale lock file to clean up. Returns the open handle (keep it
    referenced for the process lifetime) or None if another daemon holds it.
    """
    f = open(path, "a+")
    f.seek(0)
    try:
        if sys.platform == "win32":
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def _sunrise_lookup(place: pc.Place):
    """Cached (sunrise, tithi) for the vedic day containing t. Panchanga is the
    slow part; state_at is pure arithmetic. The permutation test leans on this."""
    @functools.lru_cache(maxsize=4096)
    def by_day(d: date, before_noon: bool):
        probe = datetime.combine(d, datetime.min.time(),
                                 tzinfo=place.zone) + timedelta(hours=0 if before_noon else 12)
        p = pc.compute(probe, place)
        return p.sunrise, p.tithi_index

    def lookup(t: datetime):
        t = t.astimezone(place.zone)
        sr, ti = by_day(t.date(), t.hour < 12)
        if t < sr:                       # before today's sunrise -> yesterday's vedic day
            sr, ti = by_day(t.date() - timedelta(days=1), False)
        return sr, ti

    return lookup


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
    print(f"\n  {pan.sunrise:%a %d %b} sunrise {pan.sunrise:%H:%M} → {end:%H:%M} "
          f"· {place.name}")
    print(f"  {pan.paksha} {pan.tithi_name} · sunrise current: "
          f"{SVARAS[sunrise_svara(pan.tithi_index)].english}\n")
    for e in timeline(pan.sunrise, pan.tithi_index, pan.sunrise, end, rules):
        if e.kind == "svara":
            s = SVARAS[e.svara]
            print(f"  {e.when:%H:%M}  ══ {s.emoji} {s.english.upper()} ({s.nostril}) ══")
        elif e.kind == "tattva":
            t = TATTVAS[e.tattva]
            print(f"  {e.when:%H:%M}      {t.emoji} {t.sanskrit:<12} {t.english}")
    print()


def cmd_test(cfg: dict) -> int:
    """Prove the pipe works, end to end, before trusting the daemon to it."""
    place, _ = build(cfg)
    tok, chat = cfg["telegram"]["token"], cfg["telegram"]["chat_id"]

    print(f"  token   : {'set (' + tok[:8] + '…)' if tok else 'MISSING'}")
    print(f"  chat_id : {chat or 'MISSING'}")
    if not tok or not chat:
        print("\n  Put both in .env (see .env.example), then re-run.\n")
        return 1

    tg = Telegram(tok, chat)
    me = tg.get_me()
    if not me:
        print("\n  getMe failed — the token is wrong or revoked.\n")
        return 1
    print(f"  bot     : @{me['username']}  ✓")

    sent = tg.send(test_message(me["username"], place.name), ask=datetime.now(place.zone))
    if not sent:
        print("\n  sendMessage failed. Almost always the chat id:\n"
              "    1. message your bot from your own Telegram account, then\n"
              "    2. open https://api.telegram.org/bot<TOKEN>/getUpdates\n"
              "    3. copy result[0].message.chat.id into .env\n")
        return 1

    print("  sent    : ✓  check your phone\n")
    print("  Waiting 60s for a button tap…")
    for _ in range(30):
        for tap in tg.poll():
            tg.ack(tap, matched=True)
            print(f"  tap     : ✓ received '{tap['observed']}' — buttons work.\n")
            return 0
        time.sleep(2)
    print("  no tap received — sending works, buttons untested.\n")
    return 0


def cmd_digest(cfg: dict, dry: bool) -> None:
    place, rules = build(cfg)
    tg = Telegram(cfg["telegram"]["token"], cfg["telegram"]["chat_id"], dry)
    now = datetime.now(place.zone)
    pan = pc.compute(now, place)
    st = state_at(now, pan.sunrise, pan.tithi_index, rules)
    tg.send(digest_message(pan, st, now))


def cmd_stats(cfg: dict) -> None:
    place, rules = build(cfg)
    records = lb.load()
    if not records:
        print("\n  No observations yet. Run the daemon and tap the buttons.\n")
        return

    s = lb.summarise(records)
    print(f"\n  {s['total']} observations · {s['scored']} scored · "
          f"{s['sushumna_reported']} reported as both")
    print(f"  median answer lag: {s['median_lag_s']}s\n")
    print(f"  raw match rate: {s['match_rate']:.1%}")

    if s["scored"] < 30:
        print(f"\n  Too few to test ({s['scored']}/30). Keep logging.\n")
        return

    print("\n  by element")
    for k, v in s["by_tattva"].items():
        print(f"    {TATTVAS[k].sanskrit:<12} {v['rate']:>6.1%}  (n={v['n']})")
    print("\n  by fortnight")
    for k, v in s["by_paksha"].items():
        print(f"    {k:<12} {v['rate']:>6.1%}  (n={v['n']})")

    print("\n  running permutation test (2000 shuffles)…")
    r = lb.permutation_test(records, _sunrise_lookup(place), rules)
    print(f"\n  observed match rate : {r['match_rate']:.1%}")
    print(f"  null (phase-shifted): {r['null_mean']:.1%}  "
          f"[5–95%: {r['null_p05']:.1%}–{r['null_p95']:.1%}]")
    print(f"  p-value             : {r['p_value']:.4f}")
    if r["p_value"] < 0.05:
        print("\n  Above what phase-luck explains. Worth taking seriously.\n")
    else:
        print("\n  Indistinguishable from phase-luck. Note the null is NOT 50% —\n"
              "  two periodic signals partially lock by arithmetic alone.\n")


def cmd_run(cfg: dict, dry: bool, interval: int) -> None:
    """Poll; fire on every change of (svara, tattva, sushumna); capture taps."""
    place, rules = build(cfg)

    lock = _acquire_singleton(Path("pranic.lock"))
    if lock is None:
        log.error("another `pranic run` is already active in %s — refusing to "
                  "start a second daemon (two daemons double every notification, "
                  "which is the duplicate-message bug). Stop the other one first.",
                  Path.cwd())
        return

    n = cfg["notify"]
    tg = Telegram(cfg["telegram"]["token"], cfg["telegram"]["chat_id"], dry)

    last_key = None
    last_digest_date = None
    last_positions: dict | None = None      # planet key -> (rashi, nakshatra, pada)
    log.info("watching %s · period=%dmin · order=%s · dry_run=%s",
             place.name, rules.swara_period, rules.tattva_order, dry)

    while True:
        try:
            now = datetime.now(place.zone)
            pan = pc.compute(now, place)
            st = state_at(now, pan.sunrise, pan.tithi_index, rules)
            key = (st.svara.key, st.tattva.key, st.sushumna)

            # 1. capture any button taps waiting for us
            for tap in tg.poll():
                at = datetime.fromtimestamp(tap["epoch"], tz=place.zone)
                sr, ti = _sunrise_lookup(place)(at)
                rec = lb.make_record(at, now, tap["observed"], sr, ti, rules)
                if lb.already_logged(rec.at):        # ← new
                    tg.ack(tap, matched=rec.match)   # ← new
                    continue                         # ← new
                lb.append(rec)
                tg.ack(tap, matched=rec.match)
                log.info("logged %s: prescribed=%s observed=%s match=%s",
                         at.strftime("%H:%M"), rec.prescribed, rec.observed, rec.match)

            # 2. the sunrise digest
            if n["sunrise_digest"] and last_digest_date != pan.sunrise.date() \
                    and now >= pan.sunrise:
                tg.send(digest_message(pan, st, now))
                last_digest_date = pan.sunrise.date()

            # 3. transitions
            if last_key is None:
                last_key = key                      # don't fire on cold start
            elif key != last_key:
                prev_svara, prev_tattva, prev_sush = last_key
                if st.sushumna and not prev_sush:
                    kind = "sushumna_open"
                elif st.svara.key != prev_svara:
                    kind = "svara"
                elif st.tattva.key != prev_tattva:
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
                    ask = st.next_svara_change - timedelta(minutes=rules.swara_period)
                    tg.send(transition_message(st, kind),
                            ask=ask if (kind == "svara" and n["ask_observation"]) else None)
                last_key = key

            # 4. planetary transits — fire on any rāśi/nakṣatra/pada change
            if n["transits"]:
                grahas = pc.graha_positions(pc.to_jd(now))
                if last_positions is None:
                    last_positions = {g.key: g.position for g in grahas}   # cold start
                else:
                    t_muted = _quiet(now, cfg) and not n["quiet_allows_transits"]
                    for g in grahas:
                        prev = last_positions.get(g.key)
                        if prev and g.position != prev:
                            if not t_muted:
                                tg.send(transit_message(g, prev))
                            last_positions[g.key] = g.position   # advance even if muted

        except Exception:                            # never let the daemon die
            log.exception("cycle failed; retrying")
        time.sleep(interval)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="pranic")
    ap.add_argument("command",
                    choices=["now", "today", "test", "digest", "run", "stats"])
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
    elif a.command == "test":
        return cmd_test(cfg)
    elif a.command == "digest":
        cmd_digest(cfg, a.dry_run)
    elif a.command == "stats":
        cmd_stats(cfg)
    else:
        cmd_run(cfg, a.dry_run, a.interval)
    return 0


if __name__ == "__main__":
    sys.exit(main())
