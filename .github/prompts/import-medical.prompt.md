---
description: "Import a medical document (PDF, HTML, TXT) into Vitalis. Extracts text, categorizes, and indexes for cross-referencing with Garmin data."
agent: "vitalis"
argument-hint: "Path to medical document (e.g., C:/docs/blood-test.pdf)"
---

ייבא מסמך רפואי למערכת ויטליס:

1. קבל את הנתיב למסמך מהמשתמש
2. שאל על קטגוריה (blood_tests, doctor_visits, imaging, prescriptions, vaccinations)
3. שאל על תאריך וכותרת
4. הרץ `python scripts/import_medical.py --file <path> --category <cat> --date <date> --title <title>`
5. ודא שהייבוא הצליח ב-`data/medical/index.json`
6. הצג סיכום של מה חולץ מהמסמך
