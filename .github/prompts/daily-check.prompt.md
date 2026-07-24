---
description: "Quick daily health check — sync today's data and compare to recent averages. Brief Hebrew summary."
agent: "Vitalis"
---

בדיקת בריאות יומית מהירה עבור `user_id` מפורש. אם לא סופק `user_id`, עצור ובקש אותו; לעולם אל תניח שזה הבעלים.

1. סנכרן ישירות את היום ואתמול מחשבון Garmin המבודד של המשתמש:

	```powershell
	python scripts/sync.py --user-id <user-id> --days 2
	```

	אם Garmin נכשל, המשך עם ה-packet האחרון ואל תשתמש ב-token של משתמש אחר.
2. בנה packet מפורש ל-7 ימים:

	```powershell
	python scripts/prepare_weekly_review.py --user-id <user-id> --days 7
	```
3. בדוק `nutrition_goal_audit`. אם היעד `valid`, אל תכתוב אותו מחדש. אם הוא
	`missing/stale/inconsistent`, הפעל את אותו Goal Gate של `/weekly-review`:
	חישוב nutrition-coach, שמירה עם `scripts/set_goals.py --user-id`, בניית
	packet מחדש ואימות. אם חסרים inputs או נדרש medical review, אל תשתמש
	בדיפולט וכתוב את החסם במפורש.
4. השווה את אתמול לממוצע האחרון (7 ימים)
5. סיכום קצר בעברית: מה היה טוב, מה צריך תשומת לב
6. אל תכתוב סיכום מלא — רק עדכון מהיר

**נתוני אפליקציה:** קרא תזונה וביומטריקה רק מתוך ה-packet המבודד של `user_id`; אין להשתמש במפתח legacy של הבעלים למשתמש אחר.

**פרסום יומי (אופציונלי, כבוי כברירת מחדל):** אם מתבקש פרסום, כתוב ל-`data/users/<user-id>/reports/` ופרסם למשתמש המפורש:

```powershell
python scripts/publish_summary.py --user-id <user-id> --date YYYY-MM-DD
```

ודא `"notified": 1` (השרת שלח push). אחרת — השאר את היומי בלי פרסום.
