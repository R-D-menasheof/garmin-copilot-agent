---
description: "Sync latest Garmin data from Garmin Connect. Fetches last 7 days by default."
agent: "vitalis"
---

סנכרן את הנתונים העדכניים מ-Garmin Connect:

1. בדוק את תאריך הסנכרון האחרון ב-`data/profile.yaml`
2. הרץ `python scripts/sync.py --days 7`
3. ודא שהסנכרון הצליח (תיקייה חדשה ב-`data/synced/`)
4. דווח מה הורד — כמה סוגי נתונים, טווח תאריכים
