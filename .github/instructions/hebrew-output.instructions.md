---
description: "Hebrew output rules for Vitalis health reports and summaries. Use when writing health analysis reports, summaries, or user-facing health content."
applyTo: "data/summaries/**"
---

# Hebrew Output Rules

## Language

- **Hebrew prose** — all text, section headers, and table headers in Hebrew
- **English technical terms** stay in English: VO2max, HRV, Body Battery, SpO2, REM, RHR, BMI, WHO, TDEE, LDL, HDL, HbA1c, eGFR, BMR, Deep sleep, Training Readiness
- **vitalis-meta JSON block** stays in English (machine-readable)

## Formatting

- Use ↑↓→ arrows for trend indicators
- Use 🏆 for best values, 🔴 for critical values, ⚠️ for warnings, ✅ for normal
- Tables: Hebrew headers with English metric names where appropriate
- Numbers: use commas for thousands (9,162 not 9162)
- Dates: YYYY-MM-DD format in tables, Hebrew day names in prose (יום ג׳, יום ד׳)

## Disclaimers

Include when giving medical, nutrition, or fitness advice:

- Medical: "אני לא רופא — המלצה להתייעץ עם מומחה"
- Nutrition: "זו לא המלצה רפואית — התייעץ עם רופא/תזונאית"
- Fitness: "התאם את התוכנית לתחושת הגוף"
