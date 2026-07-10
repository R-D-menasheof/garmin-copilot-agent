---
description: "Run weekly health review — sync latest Garmin data, analyze all metrics, and generate a comprehensive Hebrew health report with recommendations from nutrition, fitness, and health consultants."
agent: "vitalis"
---

בצע ביקורת שבועית מלאה עבור `user_id` מפורש. אם לא סופק `user_id`, עצור ובקש אותו — אסור להשתמש בנתוני ברירת המחדל של הבעלים.

1. **סנכרן ישירות מ-Garmin למשתמש הנכון** לפני בניית ה-packet:

   ```powershell
   python scripts/sync.py --user-id <user-id> --days 7 --non-interactive
   ```

   לכל משתמש יש OAuth tokens נפרדים תחת `data/users/<user-id>/.garmin_tokens/`.
   אסור ליפול ל-`data/.garmin_tokens/` או ל-`GARMIN_EMAIL` של הבעלים. אם Garmin
   נכשל זמנית או דורש MFA/tokens, אל תבקש input. תעד את הכשל והמשך עם נתוני
   הענן האחרונים — אל תערבב משתמשים.
2. **הכן Context Packet יחיד** לתקופה. זו אמת המידה היחידה של כל ה-agents:

   ```powershell
   python scripts/prepare_weekly_review.py --user-id <user-id> --end YYYY-MM-DD > weekly-context.json
   ```

   אין לקרוא `data/profile.yaml`, `data/summaries/` או API עם מפתח הבעלים בזמן ריצה למשתמש אחר.
3. **בדוק איכות נתונים** מתוך `data_quality`, כולל `sync_freshness` ו-`last_synced`. בדוק גם את `source`; שדות `body_battery_*`, `stress_*`, `training_readiness`, `activity_types` ו-`sleep_score` מגיעים מ-`garmin_direct` כשנתמכים בשעון. אין להשלים מדד שאינו נתמך בהשערה. אם אין דו"ח קודם, הפעל `baseline mode` בלי מגמות מלאכותיות.
4. **התייעצות עם 3 agents מומחים במקביל** — העבר לכל אחד את אותו Context Packet:
   - שאל את `nutrition-coach` — מה ההמלצות שלו לתזונה ותוספים בהתבסס על **הארוחות שתועדו בפועל** ועל הנתונים?
   - שאל את `fitness-coach` — מה תוכנית האימונים המומלצת בהתבסס על מצב ההתאוששות?
   - שאל את `health-consultant` — יש דגלים רפואיים, תובנות שינה, או חשש recovery?
5. **סינתזה** — health-analyst מאחד כפילויות וסתירות. ברירת המחדל היא 3–5 המלצות; עד 7 רק כשיש הצדקה ברורה.
6. **דו"ח אדפטיבי בעברית**:
   - השבוע במשפט אחד
   - איכות וכיסוי הנתונים
   - לוח מטרות קצר
   - מגמות או Baseline
   - תובנות תזונה, פעילות/התאוששות ובריאות/שינה
   - 3–5 פעולות מתועדפות
   - מידע חסר ושאלות המשך
7. **כתיבה** ל-`data/users/<user-id>/reports/YYYY-MM-DD.md`.
8. **פרסום idempotent** למשתמש הנכון:

   ```powershell
   python scripts/publish_summary.py --user-id <user-id> --date YYYY-MM-DD
   ```

   `status=unchanged` הוא הצלחה בריצה חוזרת ואסור לשלוח Push נוסף. `notified=0` יכול לציין שאין טוקן או שהדו"ח לא השתנה.
9. **שאלות** למשתמש על מידע חסר או אנומליות, בלי לעכב את כתיבת הדו"ח.
