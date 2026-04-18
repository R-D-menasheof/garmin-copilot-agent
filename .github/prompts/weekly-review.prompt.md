---
description: "Run weekly health review — sync latest Garmin data, analyze all metrics, and generate a comprehensive Hebrew health report with recommendations from nutrition, fitness, and health consultants."
agent: "vitalis"
---

בצע ביקורת שבועית מלאה:

1. **סנכרן** את הנתונים העדכניים מ-Garmin Connect (7 ימים אחרונים). אם סנכרון API נכשל, בדוק אם יש CSVs ב-`data/csv from garmin/` והשתמש ב-`scripts/import_garmin_csv.py`.
2. **ניתוח** מלא של כל המדדים — שינה, כושר, התאוששות, הרכב גוף, תזונה (כולל ארוחות שתיעדו באפליקציה דרך `scripts/read_nutrition.py`), בריאות כללית
3. **השוואה** לדו"ח הקודם עם מגמות ↑↓→
4. **התייעצות עם 3 agents מומחים** — זה חובה, לא אופציונלי:
   - שאל את `nutrition-coach` — מה ההמלצות שלו לתזונה ותוספים בהתבסס על **הארוחות שתועדו בפועל** ועל הנתונים?
   - שאל את `fitness-coach` — מה תוכנית האימונים המומלצת בהתבסס על מצב ההתאוששות?
   - שאל את `health-consultant` — יש דגלים רפואיים, תובנות שינה, או חשש recovery?
5. **דו"ח** מקיף בעברית עם טבלת יום-יום, מדדים, סעיף תזונה עם קלוריות/חלבון/דפוסי אכילה, והמלצות משולבות (מקסימום 7, לפי עדיפות)
6. **כתיבת סיכום** ל-`data/summaries/YYYY-MM-DD.md`
7. **שאלות** למשתמש על מידע חסר או אנומליות בנתונים (כולל ימים ללא תיעוד תזונה)
