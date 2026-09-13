# ChatGR TG **1.1.4 beta**

Кандидат в релиз: Telegram-бот **без нейросети**  
(темы, XP, монеты, квесты, викторина, дуэль, магазин, онбординг, лимиты, export).

## Запуск (одна команда)

```powershell
cd "C:\Users\User\OneDrive\Документы\MyPythonProjects"
.\start_tg_bot.bat
```

Или:

```powershell
cd "C:\Users\User\OneDrive\Документы\MyPythonProjects\ChatGR TG"
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe main.py
```

Нужен `BOT_TOKEN` в `.env` (в этой папке или в `MyPythonProjects\.env`).

Админка: `python run_admin.py` → http://127.0.0.1:8000 (`ADMIN_TOKEN`).

## Что в 1.1.4 beta

- «Причины войн» — реальный ответ, не зацикленное меню
- После игры тема не залипает на YouTube
- «Бу», «продолжи», «память», «забудь контекст»

## Что в 1.0.3

- Тема после игры не залипает на YouTube
- «Бу» / «продолжи» / «память» / «забудь контекст»

## Что в 1.0.1 beta

- После игры не залипает старая тема (YouTube и т.п.)
- «Бу» — испуг, не «мы про ютуб»
- «Продолжи» после игры — про игры

## Что в 1.0.0 beta

1. **Стабильность** — миграции БД v4, бэкап при старте и раз в 24ч, проверка backup  
2. **Онбординг** — /start: имя → квесты → викторина  
3. **Баланс** — лимит 80 XP / 40 🪙 в день, «бонус недели»  
4. **Контент** — больше квиза, факт дня, changelog  
5. **Профиль** — названия уровней, % ачивок, `/export`  
6. **Админка** — причина бана, рассылка, покупки/квиз-статы  
7. **Тесты** — pytest, `ChatGR_TG.py` = legacy  

## Команды

```
/start /help /whatsnew /profile /export
/quests /shop /play /quiz /duel /leaderboard
/memory /session
факт · бонус недели · что нового
```

## Legacy

`ChatGR_TG.py` — старый telebot+JSON. **Не используй.** Только `main.py`.

## Тесты

```powershell
$env:PYTHONPATH = (Get-Location).Path
.\.venv\Scripts\python.exe -m pytest tests -q
```
