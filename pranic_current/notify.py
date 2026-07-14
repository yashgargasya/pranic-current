"""Message composition + Telegram delivery + inline-button capture."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests

from .swara import State
from .tattva import SVARAS

if TYPE_CHECKING:                     # keeps notify.py free of the ephemeris
    from .panchanga import Graha, Panchanga

log = logging.getLogger("pranic")

BASE = "https://api.telegram.org/bot{token}/{method}"

# The three answers. One tap: the whole point is a capture surface with near-zero
# friction, 24x a day. A form you have to open is a form you won't fill in.
BUTTONS = [
    {"text": "🌙 Left", "callback_data": "o|{epoch}|ida"},
    {"text": "☀️ Right", "callback_data": "o|{epoch}|pingala"},
    {"text": "🕉️ Both", "callback_data": "o|{epoch}|both"},
]


class Telegram:
    def __init__(self, token: str, chat_id: str, dry_run: bool = False,
                 state_path: Path = Path("state.json")):
        self.token, self.chat_id, self.dry_run = token, chat_id, dry_run
        self.state_path = state_path
        self.offset = self._load_offset()

    def _load_offset(self) -> int:
        try:
            return int(json.loads(self.state_path.read_text())["offset"])
        except Exception:
            return 0

    def _save_offset(self) -> None:
        try:
            self.state_path.write_text(json.dumps({"offset": self.offset}))
        except OSError as e:
            log.warning("could not persist offset: %s", e)
    
    def _call(self, method: str, payload: dict) -> dict | None:
        for attempt in range(4):
            try:
                r = requests.post(BASE.format(token=self.token, method=method),
                                  json=payload, timeout=20)
                if r.ok:
                    return r.json()
                log.warning("telegram %s %s: %s", method, r.status_code, r.text[:200])
                if r.status_code in (400, 401, 403):
                    return None            # bad token/chat id — retrying won't help
            except requests.RequestException as e:
                log.warning("telegram %s failed: %s", method, e)
            time.sleep(2 ** attempt)
        return None

    def send(self, text: str, ask: datetime | None = None) -> dict | None:
        """Send. If `ask` is given, attach left/right/both buttons bound to it."""
        if self.dry_run or not self.token:
            print("\n" + text
                  + ("\n[ 🌙 Left ] [ ☀️ Right ] [ 🕉️ Both ]" if ask else "")
                  + "\n" + "─" * 46)
            return None

        payload: dict[str, Any] = {
            "chat_id": self.chat_id, "text": text,
            "parse_mode": "HTML", "disable_web_page_preview": True,
        }
        if ask is not None:
            epoch = int(ask.timestamp())
            payload["reply_markup"] = {"inline_keyboard": [[
                {**b, "callback_data": b["callback_data"].format(epoch=epoch)}
                for b in BUTTONS
            ]]}
        return self._call("sendMessage", payload)

    def get_me(self) -> dict | None:
        r = self._call("getMe", {})
        return r["result"] if r and r.get("ok") else None

    def poll(self) -> list[dict]:
        """Non-blocking fetch of button taps since the last call."""
        if self.dry_run or not self.token:
            return []
        r = self._call("getUpdates", {
            "offset": self.offset, "timeout": 0,
            "allowed_updates": ["callback_query"],
        })
        if not r or not r.get("ok"):
            return []
        taps = []
        for u in r["result"]:
            self.offset = max(self.offset, u["update_id"] + 1)
            cq = u.get("callback_query")
            if not cq:
                continue
            parts = cq.get("data", "").split("|")
            if len(parts) == 3 and parts[0] == "o":
                taps.append({
                    "epoch": int(parts[1]),
                    "observed": parts[2],
                    "cq_id": cq["id"],
                    "message_id": cq["message"]["message_id"],
                })
        self._save_offset()          # ← THE ONLY NEW LINE
        return taps

    def ack(self, tap: dict, matched: bool) -> None:
        """Confirm the tap, then strip the buttons so it can't be answered twice."""
        self._call("answerCallbackQuery", {
            "callback_query_id": tap["cq_id"],
            "text": "✓ logged — matches" if matched else "✓ logged — differs",
        })
        self._call("editMessageReplyMarkup", {
            "chat_id": self.chat_id, "message_id": tap["message_id"],
            "reply_markup": {"inline_keyboard": [[
                {"text": f"logged: {tap['observed']}", "callback_data": "noop"}
            ]]},
        })


# ---------- formatting ----------

def _hhmm(d: datetime) -> str:
    return d.strftime("%H:%M")


def test_message(bot_name: str, place: str) -> str:
    return (
        "🕉️ <b>Prāṇic Current — connected</b>\n\n"
        f"Bot: @{bot_name}\n"
        f"Watching: {place}\n\n"
        "If you can read this, the token and chat id are right.\n"
        "Tap a button below — it should confirm, then grey out."
    )


def transition_message(state: State, event_kind: str) -> str:
    sv, tv = state.svara, state.tattva

    if event_kind == "sushumna_open":
        s = SVARAS["sushumna"]
        return (
            f"{s.emoji} <b>Suṣumṇā — sandhi</b>\n"
            "Both nostrils level; the currents are changing over.\n\n"
            f"<i>{s.feel}</i>\n"
            f"✅ {s.favours}\n"
            f"⛔️ {s.avoid}\n\n"
            "Sit. Do not begin anything outward."
        )

    is_svara = event_kind == "svara"
    other = "right" if sv.nostril == "left" else "left"

    body = [
        # --- the current (nāḍī): what it favours, and how to confirm it ---
        f"{sv.emoji} <b>{sv.sanskrit}</b> — {sv.nostril} nostril"
        + ("  (CURRENT CHANGE)" if is_svara else ""),
        f"<i>{sv.feel}</i>",
        f"✅ do: {sv.favours}",
        f"⛔️ avoid: {sv.avoid}",
        f"🔎 check: block the {other} nostril and breathe — the {sv.nostril} "
        "should feel the freer, fuller stream.",
        "",
        # --- the element (tattva): what it favours, and how to confirm it ---
        f"{tv.emoji} <b>{tv.sanskrit}</b> ({tv.english}) · {int(tv.minutes)} min",
        f"<i>{tv.feel}</i>",
        f"✅ do: {tv.favours}",
        f"⛔️ avoid: {tv.avoid}",
        f"🔎 check: fog a cold mirror → {tv.yantra}; the breath runs {tv.direction} "
        f"({tv.angula}); taste {tv.taste}.",
        "",
        f"→ next element {_hhmm(state.next_tattva_change)} · "
        f"next current {_hhmm(state.next_svara_change)}",
    ]
    if is_svara:
        body += ["", "<b>Which nostril is actually flowing?</b>"]
    return "\n".join(body)


def digest_message(p: "Panchanga", state: State, generated_at: datetime) -> str:
    """The once-a-day sunrise context: pañcāṅga + the current opening the day.

    Deliberately does NOT list the day's transitions — those arrive one-by-one
    as each change happens, so dumping the whole schedule here is just noise.
    """
    sv = state.svara
    lines = [
        f"<b>🕉️ Prāṇic Current — {p.sunrise.strftime('%a %d %b %Y')} · "
        f"{generated_at.strftime('%H:%M')}</b>",
        f"<i>{p.place.name}</i>",
        "",
        *p.as_lines(),
        "",
        *p.sky_lines(),
        "",
        f"<b>Prescribed at sunrise:</b> {sv.emoji} {sv.sanskrit} ({sv.nostril} nostril)",
        "Verify: block one nostril, breathe, compare. If the wrong current is "
        "running, that gap is the reading.",
        "",
        "Elements cycle inside each hour: 🟨20 ⬜16 🔺12 🔵8 ⚫4 min.",
    ]
    return "\n".join(lines)


def transit_message(g: "Graha", prev: tuple[str, str, int]) -> str:
    """A planet changed rāśi / nakṣatra / pada. Announce the deepest thing that moved."""
    prev_rashi, prev_nak, _ = prev
    retro = " ℞ retrograde" if g.retrograde else ""
    nav = f" [{g.navamsa}]"                  # D9 sign of the new pada
    if g.rashi != prev_rashi:
        what = f"enters <b>{g.rashi}</b> (rāśi) — {g.nakshatra} pada {g.pada}{nav}"
    elif g.nakshatra != prev_nak:
        what = f"enters <b>{g.nakshatra}</b> pada {g.pada}{nav} · {g.rashi}"
    else:
        what = f"→ <b>{g.nakshatra} pada {g.pada}</b>{nav} · {g.rashi}"
    return f"{g.symbol} <b>{g.name}</b> {what}{retro}"
