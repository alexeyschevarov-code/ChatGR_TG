# ChatGR TG **0.7.0**

## Фичи

- Дневные квесты + монеты
- Викторина по категориям (30 вопросов)
- Память (имя, топ тем)
- Напоминания (фоновый loop)
- SQLite schema v2 + backup
- Админка: DAU, coins, messages 24h

## Структура

```
ChatGR TG/
  chatgr_core/core/quests.py
  chatgr_core/core/dialog.py
  chatgr_core/core/games.py
  chatgr_core/repositories/db.py   # migrations + backup_db
  chatgr_core/bot/reminders.py
  ...
```

## Запуск

```powershell
cd "ChatGR TG"
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe main.py
```
