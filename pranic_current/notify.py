"""Message composition + Telegram delivery."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import TYPE_CHECKING

import requests

from .swara import Event, State

if TYPE_CHECKING:                     # keeps notify.py free of the ephemeris
    from .panchanga import Panchanga
from .tattva import SVARAS, TATTVAS

log = logging.getLogger("pranic")

API = "https://api.telegram.org/bot{token}/sendMessage"


class Telegram:
    def __init__(self, token: str, chat_id: str, dry_run: bool = False):
        self.token, self.chat_id, self.dry_run = token, chat_id, dry_run

    def send(self, text: str) -> None:
        if self.dry_run or not self.token:
            print("\n" + text + "\n" + "─" * 46)
            return
        for attempt in range(4):
            try:
                r = requests.post(
                    API.format(token=self.token),
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": True,
                    },
                    timeout=15,
                )
                if r.ok:
                    return
                log.warning("telegram %s: %s", r.status_code, r.text[:200])
            except requests.RequestException as e:
                log.warning("telegram send failed: %s", e)
            time.sleep(2 ** attempt)
        log.error("gave up on message: %s", text[:60])


# ---------- formatting ----------

def _hhmm(d: datetime) -> str:
    return d.strftime("%H:%M")


def transition_message(state: State, event_kind: str) -> str:
    sv, tv = state.svara, state.tattva

    if event_kind == "sushumna_open":
        s = SVARAS["sushumna"]
        return (
            f"{s.emoji} <b>Suṣumṇā — sandhi</b>\n"
            f"Both nostrils level; the currents are changing over.\n\n"
            f"<i>{s.feel}</i>\n"
            f"✅ {s.favours}\n"
            f"⛔️ {s.avoid}\n\n"
            f"Sit. Do not begin anything outward."
        )

    head = "SVARA CHANGE" if event_kind == "svara" else "tattva"
    body = [
        f"{sv.emoji} <b>{sv.sanskrit}</b> — {sv.nostril} nostril"
        + (f"  ({head})" if event_kind == "svara" else ""),
        "",
        f"{tv.emoji} <b>{tv.sanskrit}</b> ({tv.english}) · {int(tv.minutes)} min",
        f"  colour — {tv.colour}",
        f"  mirror-mark — {tv.yantra}",
        f"  flow — {tv.direction}",
        f"  length — {tv.angula}",
        f"  bīja — {tv.bija} · taste — {tv.taste}",
        f"  feel — <i>{tv.feel}</i>",
        "",
        f"✅ {tv.favours}",
        f"⛔️ {tv.avoid}",
        "",
        f"→ next element {_hhmm(state.next_tattva_change)} · "
        f"next current {_hhmm(state.next_svara_change)}",
    ]
    if event_kind == "svara":
        body.insert(2, f"<i>{sv.feel}</i>")
        body.insert(3, "")
    return "\n".join(body)


def digest_message(p: "Panchanga", state: State, upcoming: list[Event]) -> str:
    sv = state.svara
    lines = [
        f"<b>🕉️ Prāṇic Current — {p.sunrise.strftime('%a %d %b %Y')}</b>",
        f"<i>{p.place.name}</i>",
        "",
        *p.as_lines(),
        "",
        f"<b>Prescribed at sunrise:</b> {sv.emoji} {sv.sanskrit} "
        f"({sv.nostril} nostril)",
        "Verify: block one nostril, breathe, compare. If the wrong current is "
        "running, that gap is the reading.",
        "",
        "<b>Today's currents</b>",
    ]
    for e in upcoming[:14]:
        if e.kind != "svara":
            continue
        s = SVARAS[e.svara]
        lines.append(f"  {_hhmm(e.when)}  {s.emoji} {s.english}")
    lines += ["", "Elements cycle inside each hour: "
              "🟨20 ⬜16 🔺12 🔵8 ⚫4 min."]
    return "\n".join(lines)
