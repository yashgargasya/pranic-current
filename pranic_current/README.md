# Prāṇic Current

A svara-yoga scheduler after the **Śiva Svarodaya**. It computes which current (iḍā / piṅgalā /
suṣumṇā) and which tattva (earth / water / fire / air / ether) *should* be flowing at any instant,
and Telegrams you at every change together with the day's pañcāṅga.

The rules it encodes — and where the manuscripts disagree — are set out in
**[docs/svara_shastra.md](docs/svara_shastra.md)**. Read that first; the code is only its executor.

```
sunrise ──► tithi at sunrise ──► Rule A: which current opens the day
                                    │
                                    ├─ Rule B: alternate every 60 min, day and night
                                    ├─ Rule C: suṣumṇā in the sandhi around each change
                                    └─ Rule D: 🟨20 ⬜16 🔺12 🔵8 ⚫4 min inside every block
```

## Layout

| File | What it holds |
|---|---|
| `docs/svara_shastra.md` | the textual rules, variants, and identification tables |
| `pranic_current/tattva.py` | reference data — colour, yantra, direction, aṅgula, bīja, uses |
| `pranic_current/swara.py` | the rule engine. **Pure** — no ephemeris, fully unit-tested |
| `pranic_current/panchanga.py` | Swiss Ephemeris: sunrise/sunset, tithi, nakṣatra, yoga, karaṇa |
| `pranic_current/notify.py` | message composition + Telegram delivery |
| `pranic_current/cli.py` | `now` / `today` / `digest` / `run` |
| `config.yaml` | place, rule variants, notification policy |

## Install

```bash
pip install -r requirements.txt      # pyswisseph, requests, PyYAML
```

`pyswisseph` runs in **Moshier mode** — no ephemeris data files, no network. Arc-second accuracy,
which is far more than tithi boundaries need.

## Telegram setup

1. Message **@BotFather** → `/newbot` → copy the token.
2. Send your new bot any message, then open
   `https://api.telegram.org/bot<TOKEN>/getUpdates` and read `result[0].message.chat.id`.
3. Export them (never commit them):

```bash
export TELEGRAM_BOT_TOKEN=123456:AA...
export TELEGRAM_CHAT_ID=987654321
```

## Use

```bash
python -m pranic_current now              # what should be flowing, right now
python -m pranic_current today            # the full timeline, sunrise → sunrise
python -m pranic_current digest --dry-run # preview the sunrise message
python -m pranic_current run              # the daemon
```

Set your latitude, longitude and timezone in `config.yaml` first — the whole system is anchored to
*your* sunrise, and a wrong longitude silently shifts every current.

## Notification policy

Defaults to **svara changes only** (24/day) plus a sunrise digest, because tattva changes are
**120/day** and will make you hate your phone. Turn them on deliberately:

```yaml
notify:
  tattva_changes: true
  quiet_hours: [22, 6]
```

`sushumna: true` fires a short alert at each sandhi — the one the text most wants you to catch.

## Deploy

```bash
# systemd
sudo tee /etc/systemd/system/pranic.service <<'EOF'
[Unit]
Description=Pranic Current
After=network-online.target
[Service]
WorkingDirectory=/opt/pranic-current
Environment=TELEGRAM_BOT_TOKEN=...
Environment=TELEGRAM_CHAT_ID=...
ExecStart=/usr/bin/python3 -m pranic_current run
Restart=always
RestartSec=30
[Install]
WantedBy=multi-user.target
EOF
sudo systemctl enable --now pranic
```

The daemon polls every 20 s and fires on any change of the `(svara, tattva, sushumna)` tuple, so a
restart never double-sends and a missed tick never desyncs it. It swallows exceptions and retries
rather than dying at 3 a.m.

## Tests

```bash
pip install pytest && pytest tests/ -q
```

The engine is deliberately ephemeris-free so the *ritual* rules can be tested independently of the
*astronomy*: `state_at(t, sunrise, tithi_index)` takes sunrise and tithi as plain inputs.

## Extending

- **Verify against your own breath.** The highest-value addition: a `/left`, `/right`, `/both`
  Telegram command that logs what was *actually* flowing against what was prescribed. The Svarodaya
  treats that gap as the real diagnostic. Store it, and after a month you have a personal dataset
  no one else has.
- Add moonrise/moonset, Rāhu-kāla, abhijit muhūrta to the digest (all trivial with swisseph).
- Push a 5-min warning before each svara change so you can finish what you're doing.

## A note on what this is

This is a contemplative-diagnostic system from a tantric lineage, encoded faithfully. The
"prescribed" current is what the *text* says should flow — not a physiological claim. The nasal
cycle is real and measurable, but it does not track the tithi. Treat the mismatch between prescribed
and observed as material for attention and practice, not as medicine, and not as a reason to
override a doctor.
