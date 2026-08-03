# ChatGR TG (beta)

Telegram-версия ChatGR **без нейросети**. Консольный релиз — отдельно: [ChatGR](https://github.com/alexeyschevarov-code/ChatGR).

## Статус

**Beta** — может меняться, не «официальный» релиз консоли.

## Запуск

```powershell
# клон
git clone https://github.com/alexeyschevarov-code/ChatGR_TG.git
cd ChatGR_TG

python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# токен бота (не коммить!)
# создай файл .env: BOT_TOKEN=...

$env:PYTHONPATH = (Get-Location).Path
python main.py
```

Или `.\start_tg_bot.ps1` / `start_tg_bot.bat` (если есть).

## Возможности (0.8.0 beta)

- Темы, XP, монеты, квесты, викторина
- Магазин, дуэль, эмодзи-ответы
- SQLite, админка (экспериментально)

## Не выкладывать

`.env`, `tg_data/`, `data/`, `logs/`, `*.db` — см. `.gitignore`.

## Автор

Лёша (alexeyschevarov-code)
