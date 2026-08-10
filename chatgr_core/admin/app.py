"""Админ-панель 1.0.0 beta: бан с причиной, рассылка, статистика."""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from chatgr_core.config import ADMIN_TOKEN, DB_PATH, VERSION
from chatgr_core.repositories.db import get_connection, init_db
from chatgr_core.repositories.users import UserRepository

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="ChatGR Admin", version=VERSION)

# last broadcast text for UI feedback
_last_broadcast: str = ""


def get_repo() -> UserRepository:
    init_db(DB_PATH)
    conn = get_connection(DB_PATH)
    return UserRepository(conn)


def check_admin(request: Request) -> None:
    token = request.cookies.get("admin_token") or request.headers.get("X-Admin-Token")
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
async def login(token: str = Form(...)):
    if token != ADMIN_TOKEN:
        return RedirectResponse("/?error=1", status_code=303)
    resp = RedirectResponse("/dashboard", status_code=303)
    resp.set_cookie("admin_token", token, httponly=True, max_age=86400)
    return resp


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, repo: UserRepository = Depends(get_repo)):
    check_admin(request)
    stats = repo.stats()
    users = repo.list_users(50)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "stats": stats,
            "users": users,
            "version": VERSION,
            "broadcast_ok": request.query_params.get("broadcast"),
        },
    )


@app.get("/users/{tg_user_id}", response_class=HTMLResponse)
async def user_detail(
    request: Request,
    tg_user_id: str,
    repo: UserRepository = Depends(get_repo),
):
    check_admin(request)
    users = [u for u in repo.list_users(500) if u["tg_user_id"] == tg_user_id]
    user = users[0] if users else None
    msgs = repo.recent_messages(tg_user_id, 30)
    reason = repo.get_ban_reason(tg_user_id)
    return templates.TemplateResponse(
        "user.html",
        {
            "request": request,
            "user": user,
            "messages": msgs,
            "tg_user_id": tg_user_id,
            "ban_reason": reason,
        },
    )


@app.post("/users/{tg_user_id}/ban")
async def ban_user(
    request: Request,
    tg_user_id: str,
    reason: str = Form(""),
    repo: UserRepository = Depends(get_repo),
):
    check_admin(request)
    repo.set_banned(tg_user_id, True, reason=reason.strip() or "без указания")
    return RedirectResponse(f"/users/{tg_user_id}", status_code=303)


@app.post("/users/{tg_user_id}/unban")
async def unban_user(
    request: Request,
    tg_user_id: str,
    repo: UserRepository = Depends(get_repo),
):
    check_admin(request)
    repo.set_banned(tg_user_id, False)
    return RedirectResponse(f"/users/{tg_user_id}", status_code=303)


@app.post("/broadcast")
async def broadcast(
    request: Request,
    text: str = Form(...),
    repo: UserRepository = Depends(get_repo),
):
    """Сохраняет текст рассылки; отправка — через бота (log only if no bot)."""
    check_admin(request)
    text = (text or "").strip()
    if not text:
        return RedirectResponse("/dashboard?broadcast=empty", status_code=303)
    # queue: write admin_logs; actual send via optional BOT if imported
    repo.log_admin("broadcast", text[:2000])
    sent = 0
    try:
        from chatgr_core.config import BOT_TOKEN
        if BOT_TOKEN:
            from aiogram import Bot

            bot = Bot(token=BOT_TOKEN)
            for uid in repo.list_user_ids():
                try:
                    await bot.send_message(
                        int(uid),
                        f"📢 <b>Сообщение ChatGR</b>\n\n{text}",
                        parse_mode="HTML",
                    )
                    sent += 1
                except Exception:
                    pass
            await bot.session.close()
    except Exception:
        pass
    repo.log_admin("broadcast_sent", f"sent={sent}")
    return RedirectResponse(f"/dashboard?broadcast={sent}", status_code=303)


@app.get("/api/stats")
async def api_stats(request: Request, repo: UserRepository = Depends(get_repo)):
    check_admin(request)
    return repo.stats()


@app.get("/api/users")
async def api_users(request: Request, repo: UserRepository = Depends(get_repo)):
    check_admin(request)
    return repo.list_users(200)
