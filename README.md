# 🏋️ garmin-copilot-agent

**Your Garmin data + GitHub Copilot = personal health adviser**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://python.org)
[![Tests](https://img.shields.io/badge/Tests-101%20passing-brightgreen.svg)](#running-tests)

An **agent-first** health analysis system. No dashboards. No servers. Just your Garmin data and GitHub Copilot as your personal health adviser.

> **⚠️ Disclaimer**: This project uses the unofficial [`python-garminconnect`](https://github.com/cyberjunky/python-garminconnect) library to access Garmin Connect data. It is **not affiliated with or endorsed by Garmin**. Using unofficial APIs may violate Garmin's Terms of Service. **Use at your own risk.** Your credentials are stored locally in `.env` and never transmitted anywhere except to Garmin's servers.

---

## What is this?

Most health trackers give you dashboards and charts. This project takes a different approach — it turns **GitHub Copilot** into your personal health analyst.

The code handles the boring parts: syncing 30+ data types from Garmin Connect, storing them as raw JSON, and managing your profile. **GitHub Copilot** handles the smart parts: reading your data, comparing against health guidelines, tracking trends across sessions, and generating personalised recommendations — all through natural conversation in your editor.

```
┌──────────────┐     sync.py      ┌──────────────┐     GitHub Copilot     ┌──────────────┐
│              │ ───────────────→  │              │  ──────────────────→   │              │
│ Garmin       │   30+ data types  │ data/synced/ │   reads raw JSON +    │ Hebrew health│
│ Connect API  │                   │ (raw JSON)   │   profile + memory    │ report with  │
│              │                   │              │                       │ recommendations│
└──────────────┘                  └──────────────┘                       └──────────────┘
                                                                                │
                                                                                ▼
                                                                        ┌──────────────┐
                                                                        │ data/        │
                                                                        │ summaries/   │
                                                                        │ (agent       │
                                                                        │  memory)     │
                                                                        └──────────────┘
```

### Key concept: Agent Memory

After every analysis, Copilot writes a summary to `data/summaries/`. Before the next analysis, it reads the previous summary for context. This gives the agent **memory across sessions** — it tracks your trends, follows up on recommendations, and notices improvements or regressions over time.

---

## Features

- **30+ Garmin data types** — steps, sleep (with stages), HRV, Body Battery, VO2max, training readiness, stress, SpO2, activities, weight, respiration, intensity minutes, personal records, and more
- **Medical records** — import blood tests, doctor visits, imaging reports, prescriptions, and vaccination records (PDF, HTML, TXT); auto-extract text and cross-reference with fitness data
- **Interactive MFA** — handles Garmin's 2FA seamlessly in the terminal
- **Agent memory** — summaries with `context_for_next_run` provide continuity across sessions
- **Hebrew health reports** — comprehensive analysis in Hebrew with English technical terms (VO2max, HRV, etc.)
- **Trend tracking** — ↑↓→ arrows comparing every metric to previous analysis
- **Health science context** — each recommendation explains *why* it matters physiologically
- **Interactive profile** — the agent asks questions to fill in goals, injuries, dietary preferences
- **9 agent skills** — teach Copilot exactly how to analyze your health data
- **Structured metric extraction** — `extract_metrics.py` replaces ad-hoc data parsing

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **Garmin Connect account** with data from a Garmin device
- **VS Code** with [GitHub Copilot](https://github.com/features/copilot) (Chat)

### Setup

```bash
# Clone the repo
git clone https://github.com/R-D-menasheof/garmin-copilot-agent.git
cd garmin-copilot-agent

# Create and activate a virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure credentials
cp .env.example .env
# Edit .env with your Garmin email and password

# Configure your profile
cp data/profile.example.yaml data/profile.yaml
# Edit data/profile.yaml with your details (name, age, height, goals)
```

### Sync your data

```bash
# Sync the last 28 days
python scripts/sync.py --days 28

# On first run, you may be prompted for an MFA code:
#   "Garmin sent a verification code to your email."
#   "Enter the MFA code: ______"
# After the first successful login, tokens are saved and MFA is skipped.

# Or sync a specific date range
python scripts/sync.py --from 2026-01-01 --to 2026-01-31

# Or just today
python scripts/sync.py --today
```

### Ask Copilot for analysis

Open GitHub Copilot Chat in VS Code and ask:

> "Analyze my health data"

Copilot will:
1. Read your previous summary for context
2. Read your profile and extract metrics from synced data
3. Ask you questions about missing profile info (goals, injuries, etc.)
4. Generate a comprehensive Hebrew health report with recommendations

---

## How It Works — 4-Phase Analysis

| Phase | Name | What happens |
|-------|------|-------------|
| 1 | **Context** (קריאת הקשר) | Read latest `data/summaries/*.md` — extract previous metrics and tracking items |
| 2 | **Data** (קריאת נתונים) | Read `data/profile.yaml`, run `scripts/extract_metrics.py`, read raw JSON for detail |
| 3 | **Clarify** (שאלות למשתמש) | Ask user questions in Hebrew about missing profile info or data anomalies |
| 4 | **Report** (כתיבת דו"ח) | Generate Hebrew health report, write summary with `context_for_next_run` |

The report covers: **כושר** (fitness), **שינה** (sleep), **התאוששות** (recovery), **הרכב גוף** (body composition), **תזונה** (nutrition), and **בריאות כללית** (general health).

---

## Agent Skills

The `.github/skills/` directory teaches Copilot how to work with your data:

| Skill | File | What it teaches |
|-------|------|----------------|
| Fetch Garmin Data | `fetch-garmin-data.md` | Sync 30+ data types via CLI |
| Analyze Health Data | `analyze-health-data.md` | 4-phase analysis workflow, metrics, thresholds |
| Write Summary | `write-summary.md` | Hebrew report format, vitalis-meta block |
| Personal Profile | `personal-profile.md` | Interactive profile completion, personalisation |
| Data Layout | `data-layout.md` | JSON structures, folder layout, device compatibility |
| Agent Memory | `agent-memory.md` | Summary-based memory protocol, trend comparison |
| Health Recommendations | `health-recommendations.md` | Priority scale, categories, personalisation rules |
| Compare Days | `compare-days.md` | Day-level metric comparison |
| Garmin CSV Analysis | `garmin-csv-analysis.md` | Manual CSV upload parsing rules |
| Medical Records | `medical-records.md` | Medical record management, lab reference ranges, cross-referencing |

---

## Project Structure

```
garmin-copilot-agent/
├── src/vitalis/               # Core Python package
│   ├── garmin_client.py       # Garmin Connect API (auth, MFA, 30+ types)
│   ├── data_store.py          # Save raw JSON to date-stamped folders
│   ├── medical_store.py       # Medical record import, extraction, indexing
│   ├── profile.py             # User profile (YAML) management
│   ├── summary_store.py       # Agent memory — read/write summaries
│   └── models.py              # Pydantic models
├── scripts/
│   ├── sync.py                # CLI sync with interactive MFA
│   ├── import_medical.py      # Import medical documents
│   ├── extract_metrics.py     # Structured metric extraction
│   └── compare_days.py        # Day-level comparison
├── tests/                     # pytest tests (126 passing)
├── data/
│   ├── profile.yaml           # Your profile (gitignored)
│   ├── synced/                # Raw Garmin data (gitignored)
│   ├── medical/               # Medical records (gitignored)
│   ├── summaries/             # Agent memory (gitignored)
│   └── samples/               # Sample data for development
├── .github/
│   ├── copilot-instructions.md    # Agent behavior rules
│   └── skills/                    # 10 skill definitions
├── pyproject.toml             # Package config
├── .env.example               # Credential template
├── data/profile.example.yaml  # Profile template
└── LICENSE                    # MIT
```

---

## Helper Scripts

### Extract Metrics

Get a structured summary of all metrics from synced data:

```bash
python scripts/extract_metrics.py              # Latest sync folder
python scripts/extract_metrics.py --json        # JSON output
python scripts/extract_metrics.py --folder 2026-01-19_to_2026-02-15
```

### Compare Days

Compare specific days side-by-side:

```bash
python scripts/compare_days.py 2026-02-13 2026-02-14
python scripts/compare_days.py 2026-02-13 2026-02-14 --json
python scripts/compare_days.py 2026-02-13 --folder 2026-01-19_to_2026-02-15
```

### Import Medical Records

Import medical documents (PDF, HTML, TXT) for cross-referencing with Garmin data:

```bash
# Import a blood test PDF
python scripts/import_medical.py --file ~/Downloads/blood_test.pdf --category blood_test --date 2026-03-01 --title "Lipid Panel"

# Import a doctor visit summary
python scripts/import_medical.py --file report.html --category doctor_visit --date 2026-03-01 --title "Annual Checkup"

# Import with auto-detected title from filename
python scripts/import_medical.py --file ~/Downloads/cbc_results.pdf --category blood_test

# Rebuild the index after manual file placement
python scripts/import_medical.py --rebuild-index
```

Categories: `blood_test`, `doctor_visit`, `imaging`, `prescription`, `vaccination`

Documents are stored in `data/medical/` (gitignored). Text is auto-extracted from PDFs and HTML files. The agent cross-references lab values with Garmin fitness data during analysis.

---

## Customisation

### Adding goals

Edit `data/profile.yaml` or let the agent ask you during analysis:

```yaml
goals:
  - Lose weight to 90 kg
  - Sleep 7+ hours consistently
  - Improve VO2max above 40
```

### Modifying skills

Skills are plain Markdown files in `.github/skills/`. Edit them to change:
- Analysis thresholds (e.g., what counts as "short sleep")
- Recommendation categories and priorities
- Report format and language
- Data type handling

### Adding data types

The `garminconnect` library supports many endpoints. To add a new data type:
1. Add a fetch method in `src/vitalis/garmin_client.py`
2. Add extraction logic in `scripts/extract_metrics.py`
3. Update the relevant skill file to document the new data

---

## Privacy

All data stays on your machine:

- **Credentials** (`.env`) — gitignored, never committed
- **OAuth tokens** (`data/.garmin_tokens/`) — gitignored
- **Health data** (`data/synced/`) — gitignored
- **Medical records** (`data/medical/`) — gitignored
- **Profile** (`data/profile.yaml`) — gitignored
- **Analysis summaries** (`data/summaries/`) — gitignored

Nothing is sent to any server except Garmin's own API (for data sync).

---

## Running Tests

```bash
pytest tests/ -q
```

All 126 tests cover: Garmin client auth/MFA, data store, profile management, summary store, sync CLI, metric extraction (39 tests), day comparison (12 tests), and medical records (25 tests).

---

## Requirements

| Requirement | Version |
|------------|---------|
| Python | 3.11+ |
| garminconnect | ≥0.2 |
| pydantic | ≥2.0 |
| pyyaml | ≥6.0 |
| python-dotenv | ≥1.0 |
| pymupdf | ≥1.24 |
| beautifulsoup4 | ≥4.12 |
| lxml | ≥5.0 |
| VS Code + GitHub Copilot | Latest |

---

## Contributing

Contributions are welcome! Please:

1. Fork the repo
2. Create a feature branch (`git checkout -b feat/my-feature`)
3. Write tests first (TDD)
4. Run `pytest` to verify
5. Submit a PR with a clear description

See [copilot-instructions.md](.github/copilot-instructions.md) for coding conventions.

---

## Acknowledgements

- [**python-garminconnect**](https://github.com/cyberjunky/python-garminconnect) by [@cyberjunky](https://github.com/cyberjunky) — the unofficial Garmin Connect library that makes this project possible
- [**GitHub Copilot**](https://github.com/features/copilot) — the AI that serves as the analysis engine

---

## License

[MIT](LICENSE) © R-D-menasheof
