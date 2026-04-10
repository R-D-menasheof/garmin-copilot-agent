---
name: medical-records
description: "Medical record management — import, extraction, indexing, lab reference ranges, cross-referencing with Garmin data. Use when: importing medical documents, interpreting blood tests, cross-referencing lab values with health metrics."
---

# Skill: Medical Records

## Overview

Vitalis manages medical records (blood tests, doctor visits, imaging reports, prescriptions, vaccinations) alongside Garmin fitness data. Documents are imported, text-extracted, and stored locally under `data/medical/`. The agent cross-references medical data with fitness data to provide unified health recommendations.

## Storage Layout

```
data/medical/
├── blood_tests/
│   └── 2026-03-01_lipid-panel/
│       ├── original.pdf         # Raw uploaded document
│       ├── extracted.json       # Auto-extracted text + metadata (MedicalRecord model)
│       └── notes.md             # Optional manual notes/corrections
├── doctor_visits/
│   └── YYYY-MM-DD_slug/
├── imaging/
│   └── YYYY-MM-DD_slug/
├── prescriptions/
│   └── YYYY-MM-DD_slug/
├── vaccinations/
│   └── YYYY-MM-DD_slug/
├── context.md                   # Persistent medical summary (agent-maintained)
└── index.json                   # Auto-generated master index
```

### Conventions

- Each document lives in a subfolder: `{category}/{YYYY-MM-DD}_{slug}/`
- `original.*` — the raw file (PDF, HTML, TXT, image), never modified
- `extracted.json` — structured sidecar with full `MedicalRecord` model (text, metadata, parsed values)
- `index.json` — convenience cache, auto-rebuilt with `--rebuild-index`
- All files in `data/medical/` are **gitignored** — personal data never leaves the machine

## How to Read Medical Records

### Step 1: Check what's available

Read `data/medical/index.json` to get a list of all imported records:

```json
{
  "records": [
    {
      "category": "blood_tests",
      "date": "2026-03-01",
      "title": "Lipid Panel",
      "language": "he",
      "source_file": "blood_tests/2026-03-01_lipid-panel/original.pdf",
      "extracted_text": "...",
      "parsed_values": {
        "LDL": { "value": 130, "unit": "mg/dL", "reference": "<100" }
      },
      "tags": ["cholesterol"],
      "notes": ""
    }
  ],
  "last_updated": "2026-03-01T10:30:00"
}
```

### Step 2: Read extracted text

For each relevant record, read the `extracted_text` field from the index or open the `extracted.json` sidecar file directly.

### Step 3: Interpret and cross-reference

See "Cross-Referencing" section below.

## Importing Documents

Users import documents via CLI:

```bash
python scripts/import_medical.py --file path/to/doc.pdf --category blood_test --date 2026-03-01 --title "Lipid Panel"
python scripts/import_medical.py --file report.html --category doctor_visit --date 2026-03-01 --title "Annual Checkup"
python scripts/import_medical.py --rebuild-index
```

Categories: `blood_test`, `doctor_visit`, `imaging`, `prescription`, `vaccination`

Supported formats:

- **PDF** → text extracted via PyMuPDF
- **HTML** → text extracted via BeautifulSoup
- **TXT / MD** → read directly
- **Images (JPG, PNG)** → stored but no text extraction (future OCR)

## Important: Blood Test Import Is Two-Step

When the user imports historical or new **blood tests**, importing the document into `data/medical/` is only the first step.

### Step A — Local medical record

- Import the document into `data/medical/`
- Rebuild / verify `data/medical/index.json`
- Add concise `notes` if the important values are obvious and useful for future analysis

### Step B — App-facing lab trends

The mobile app's **Lab Trends** tab does **not** read raw `data/medical/` documents directly. It reads a separate API dataset from `/api/v1/medical/lab-trends`.

If the imported blood test contains chart-worthy numeric values, the agent should also update lab trends so the app reflects the same history.

Typical trend metrics to sync when available:

- Lipids: `LDL`, `HDL`, `total_cholesterol`, `triglycerides`
- Metabolic: `glucose`, `HbA1c`
- Liver: `ALT`, `AST`
- Kidney: `creatinine`, `eGFR`
- Vitamins / iron: `vitamin_d`, `vitamin_b12`, `ferritin`
- Inflammation / thyroid: `CRP`, `TSH`

### Lab Trend Sync Rules

- **Merge with existing trend history** — do not overwrite useful later data with an older partial series
- Use the **actual test date** from the document, not today's date
- Only include values that are clearly readable and attributable to a specific metric
- If a document is a clinic summary without explicit numeric labs, import it to `data/medical/` but do not invent lab-trend points
- After writing trends, verify with `GET /api/v1/medical/lab-trends`

### Why this matters

Without this second step, the app can show stale or incomplete lab charts even though the PDFs were correctly imported into `data/medical/`.

## Common Lab Values Reference

When interpreting blood test results, use these reference ranges:

### Complete Blood Count (CBC) — ספירת דם

| Test (English) | Test (Hebrew)  | Normal Range | Unit    |
| -------------- | -------------- | ------------ | ------- |
| WBC            | כדוריות לבנות  | 4.5–11.0     | ×10³/µL |
| RBC (M)        | כדוריות אדומות | 4.7–6.1      | ×10⁶/µL |
| RBC (F)        | כדוריות אדומות | 4.2–5.4      | ×10⁶/µL |
| Hemoglobin (M) | המוגלובין      | 14.0–18.0    | g/dL    |
| Hemoglobin (F) | המוגלובין      | 12.0–16.0    | g/dL    |
| Hematocrit (M) | המטוקריט       | 42–52        | %       |
| Hematocrit (F) | המטוקריט       | 37–47        | %       |
| Platelets      | טסיות          | 150–400      | ×10³/µL |

### Lipid Panel — פרופיל שומנים

| Test              | Hebrew        | Optimal | Borderline | High |
| ----------------- | ------------- | ------- | ---------- | ---- |
| Total Cholesterol | כולסטרול כללי | <200    | 200–239    | ≥240 |
| LDL               | כולסטרול רע   | <100    | 100–159    | ≥160 |
| HDL (M)           | כולסטרול טוב  | >40     | —          | <40  |
| HDL (F)           | כולסטרול טוב  | >50     | —          | <50  |
| Triglycerides     | טריגליצרידים  | <150    | 150–199    | ≥200 |

### Metabolic Panel — כימיה בדם

| Test              | Hebrew           | Normal Range | Unit   |
| ----------------- | ---------------- | ------------ | ------ |
| Glucose (fasting) | גלוקוז           | 70–100       | mg/dL  |
| HbA1c             | המוגלובין מסוכרר | <5.7         | %      |
| Creatinine (M)    | קריאטינין        | 0.7–1.3      | mg/dL  |
| Creatinine (F)    | קריאטינין        | 0.6–1.1      | mg/dL  |
| BUN               | אוריאה           | 7–20         | mg/dL  |
| eGFR              | סינון גלומרולרי  | >60          | mL/min |

### Thyroid — בלוטת התריס

| Test    | Hebrew                  | Normal Range | Unit  |
| ------- | ----------------------- | ------------ | ----- |
| TSH     | הורמון מגרה בלוטת התריס | 0.4–4.0      | mIU/L |
| Free T4 | תירוקסין חופשי          | 0.8–1.8      | ng/dL |
| Free T3 | טריודותירונין חופשי     | 2.3–4.2      | pg/mL |

### Iron Studies — ברזל

| Test     | Hebrew          | Normal Range (M) | Normal Range (F) | Unit  |
| -------- | --------------- | ---------------- | ---------------- | ----- |
| Iron     | ברזל            | 65–175           | 50–170           | µg/dL |
| Ferritin | פריטין          | 20–250           | 10–120           | ng/mL |
| TIBC     | כושר קשירת ברזל | 250–370          | 250–370          | µg/dL |

### Vitamins — ויטמינים

| Test        | Hebrew      | Normal Range | Unit  |
| ----------- | ----------- | ------------ | ----- |
| Vitamin D   | ויטמין D    | 30–100       | ng/mL |
| Vitamin B12 | ויטמין B12  | 200–900      | pg/mL |
| Folate      | חומצה פולית | >3.0         | ng/mL |

## Cross-Referencing Medical + Garmin Data

When both medical records and Garmin data are available, the agent should find connections:

| Medical Data         | Garmin Data                | What to Look For                                                                    |
| -------------------- | -------------------------- | ----------------------------------------------------------------------------------- |
| Hemoglobin / Iron    | VO2max, Training Readiness | Low iron → VO2max decline, fatigue, poor recovery                                   |
| Thyroid (TSH, T3/T4) | RHR, Body Battery, Weight  | Hypothyroid → high RHR, low BB, weight gain; Hyper → low RHR, weight loss           |
| Glucose / HbA1c      | Body composition, Activity | Pre-diabetic + sedentary = urgent. Active lifestyle helps insulin sensitivity       |
| Vitamin D            | Sleep, Recovery, Stress    | Low vitamin D correlates with poor sleep quality and slower recovery                |
| Lipid panel          | Activity volume, VO2max    | High LDL + low activity = cardiovascular risk. Improving VO2max helps HDL           |
| Creatinine / eGFR    | Hydration, Training load   | High creatinine with heavy training may be benign (muscle mass). Low eGFR = concern |
| Vitamin B12          | Fatigue, Body Battery      | Low B12 → chronic fatigue, poor Body Battery recharge                               |
| Medications          | RHR, HRV, Sleep            | Beta blockers lower RHR/HRV (expected). SSRIs may affect sleep stages               |

### Medication Awareness

The user's `current_medications` list in `data/profile.yaml` should be checked against Garmin metrics:

- **Beta blockers** → RHR and HRV will be artificially lower; don't alarm on low values
- **Statins** → if prescribed, check lipid panel trends for improvement
- **Thyroid meds** → compare TSH to target range, correlate with energy/weight trends
- **Metformin** → glucose/HbA1c should be trending down; check B12 (metformin depletes it)

## Privacy Rules

- **Never include raw medical data** in summaries shared externally
- **Extracted text stays local** — `data/medical/` is gitignored
- **In summaries**, reference lab values by metric name only (e.g., "LDL improved to 120 mg/dL") — don't dump full reports
- **In `metrics_snapshot`**, include key medical values for trend tracking (e.g., `"latest_ldl": 130, "latest_hba1c": 5.4`)

## Language Handling

Medical documents may be in Hebrew or English:

- **Auto-detection**: The system checks for Hebrew Unicode characters (U+0590–U+05FF). If >5% of non-whitespace chars are Hebrew → classified as "he"
- **Hebrew lab reports**: Common Israeli lab providers (Maccabi, Clalit, Meuhedet) output Hebrew PDF reports
- **Mixed documents**: Some documents have Hebrew prose with English test names — these are classified as "he"
- **The agent reads both** — extracted text is in the original language, the agent interprets it regardless

## Medical Context File (`data/medical/context.md`)

The agent maintains a persistent `context.md` file in `data/medical/` that summarizes all medical knowledge across sessions. This file is gitignored (personal data).

### When to read it

- **Every analysis** — read `context.md` in Phase 1 alongside the fitness summary's `context_for_next_run`
- It contains active recommendations, follow-up questions, and medical trend summaries

### When to update it

- After analyzing medical records (blood tests, imaging reports, etc.)
- After the user reports health changes (supplements, lifestyle, symptoms)
- After receiving answers to follow-up questions
- After importing historical blood tests, especially if they materially change the long-term picture (for example 2020 → 2022 → 2025 comparisons)

### What it contains

- **Key Medical Findings** — summarized trends from blood tests, imaging, etc.
- **Active Recommendations** — numbered, actionable items with targets
- **Questions to Ask Next Time** — in Hebrew, things to follow up on

### Profile fields for health context

The agent should also check these `profile.yaml` fields:

- **`current_medications`** — prescribed medications (name, dosage, frequency, what it's for)
- **`supplements`** — self-administered supplements (name, dosage, timing, since)
- **`health_log`** — timestamped notes about lifestyle changes, symptoms, events
- When the user reports changes, update these fields AND `context.md`
