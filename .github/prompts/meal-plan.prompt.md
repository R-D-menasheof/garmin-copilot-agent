---
description: "Get personalized nutrition advice — calorie targets, macro splits, supplement recommendations, and meal guidance based on your Garmin data, blood work, goals, and dietary preferences."
agent: "Vitalis"
---

תן ייעוץ תזונתי מותאם אישית עבור `user_id` מפורש. אם לא סופק `user_id`, עצור
ובקש אותו; אין להשתמש בפרופיל או ביעד של הבעלים כברירת מחדל.

1. בנה Context Packet מבודד עם
	`python scripts/prepare_weekly_review.py --user-id <user-id> --days 14`.
2. קרא ממנו בלבד את הפרופיל, היעדים, הארוחות, בדיקות הדם, התרופות והתוספים.
3. בדוק `nutrition_goal_audit` והפעל את Calculation Output Contract של
	`nutrition-coach`. אל תחשב או תציג יעד דיפולטיבי כשחסר input.
4. אם הסטטוס `missing/stale/inconsistent` והוחזר `calculated`, שמור עם:

	```powershell
	python scripts/set_goals.py --user-id <user-id> --calories <kcal> --protein <g> --carbs <g> --fat <g> --weight <kg> --tdee <kcal> --calculation-method mifflin_st_jeor+garmin
	```

5. בנה packet מחדש ואמת exact read-back ו-`nutrition_goal_status=valid`. אם
	חסרים פרטים או נדרש medical review, אל תשמור יעד והצג את החסם.
6. תן המלצות ספציפיות עם מספרים ותוכנית ארוחות התואמת ליעד המאומת בלבד.
7. התחשב רק בהקשר הרפואי, התרופתי ובבדיקות המעבדה שמופיעים ב-packet של
	המשתמש הנוכחי; אל תכניס אבחנות או ערכים שאינם קיימים בו.
