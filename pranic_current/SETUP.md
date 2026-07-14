# Setting up in VS Code + GitHub

## 0. Check the folder shape first

Your `Prana/` folder must look like this — in particular, the four modules have to sit **inside** a
`pranic_current/` subfolder, or `python -m pranic_current` won't find them.

```
Prana/
├── .github/workflows/ci.yml
├── .vscode/{settings,launch,extensions}.json
├── docs/svara_shastra.md
├── pranic_current/
│   ├── __init__.py          ← must exist, even if it were empty
│   ├── __main__.py
│   ├── cli.py
│   ├── notify.py
│   ├── panchanga.py
│   ├── swara.py
│   └── tattva.py
├── tests/test_swara.py
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── config.yaml
├── pyproject.toml
└── requirements.txt
```

In the VS Code terminal (``Ctrl+` ``):

```bash
ls pranic_current/   # should list 7 .py files. If it doesn't, move them there.
```

## 1. Virtual environment

VS Code: `Cmd/Ctrl+Shift+P` → **Python: Create Environment** → *Venv* → your 3.11+ interpreter →
tick `pyproject.toml`. That creates `.venv/`, installs everything, and selects the interpreter.

Or by hand:

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

`-e` (editable) means your edits take effect without reinstalling. It also installs the `pranic`
command, so you can type `pranic now` instead of `python -m pranic_current now`.

## 2. Secrets

```bash
cp .env.example .env             # Windows: copy .env.example .env
```

Fill in your real token and chat id. **`.env` is gitignored — keep it that way.** If a token ever
lands in a commit, treat it as burned: `/revoke` in @BotFather and issue a new one. Rewriting git
history does not un-leak it.

## 3. Run it

Press `F5`, or pick from the Run panel — the launch configs are already written:

| Config | What it does |
|---|---|
| `pranic: now` | prints the prescribed current + element right now |
| `pranic: today` | the whole vedic day, sunrise → sunrise |
| `pranic: digest (dry run)` | prints the sunrise message instead of sending it |
| `pranic: run daemon (dry run, 5s poll)` | the daemon, printing to the terminal — **start here** |
| `pranic: run daemon (LIVE)` | actually Telegrams you |

Set breakpoints in `swara.py:state_at` and step through with the dry-run daemon — that's the fastest
way to see the rules execute.

## 4. Verify the astronomy before you trust it

The single most likely bug is a wrong longitude sign (west is **negative**). Everything else is
downstream of sunrise, so a bad longitude silently shifts every current in the system.

```bash
pranic now
```

Check the printed sunrise/sunset against any local almanac or your weather app. If it's off by more
than a couple of minutes, fix `config.yaml` before going further.

## 5. Tests

```bash
pytest -q
```

Or the flask icon in the VS Code sidebar — the test explorer is already configured. The 11 checks
cover the rule engine only (Rules A–D); they need no ephemeris and no network.

## 6. Git + GitHub

```bash
git init -b main
git add .
git status                       # ← LOOK at this. .env must NOT appear.
git commit -m "Pranic Current: svara engine, panchanga, Telegram notifier"
```

Then either:

```bash
gh repo create pranic-current --public --source=. --push     # needs the gh CLI
```

or make an empty repo on github.com (no README, no .gitignore — you have both) and:

```bash
git remote add origin https://github.com/<you>/pranic-current.git
git push -u origin main
```

VS Code's Source Control panel (`Ctrl+Shift+G`) does all of this with buttons if you prefer, and
**Publish to GitHub** handles the remote for you.

CI runs on push: ruff, mypy, the rule tests on 3.11 and 3.12, plus a smoke test that computes a real
Varanasi pañcāṅga — so a broken ephemeris call can't merge silently.

## 7. Suggested first commits

Good small changes to get into a rhythm:

1. Put **your own** lat/lon/tz in `config.yaml`. Commit.
2. Add moonrise/moonset to the digest (`swe.rise_trans` with `swe.MOON` — `panchanga.py` already has
   the wrapper).
3. Add a `/left` `/right` `/both` Telegram command that logs the current you **actually** observe
   against the one prescribed, appended to a JSONL file. This is the feature that turns the project
   from a notifier into an instrument.
