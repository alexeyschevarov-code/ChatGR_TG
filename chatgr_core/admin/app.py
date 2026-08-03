"""Админ-панель: FastAPI + Jinja2 шаблоны."""
from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from chatgr_core.config import ADMIN_TOKEN, DB_PATH
from chatgr_core.repositories.db import get_connection, init_db
from chatgr_core.repositories.users import UserRepository

TEMPLATES_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

app = FastAPI(title="ChatGR Admin", version="0.7.0")


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
    return templates.TemplateResponse(
        "login.html",
        {"request": request, "error": None},
    )


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
        {"request": request, "stats": stats, "users": users},
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
    return templates.TemplateResponse(
        "user.html",
        {"request": request, "user": user, "messages": msgs, "tg_user_id": tg_user_id},
    )


@app.post("/users/{tg_user_id}/ban")
async def ban_user(
    request: Request,
    tg_user_id: str,
    repo: UserRepository = Depends(get_repo),
):
    check_admin(request)
    repo.set_banned(tg_user_id, True)
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


@app.get("/api/stats")
async def api_stats(request: Request, repo: UserRepository = Depends(get_repo)):
    check_admin(request)
    return repo.stats()


@app.get("/api/users")
async def api_users(request: Request, repo: UserRepository = Depends(get_repo)):
    check_admin(request)
    return repo.list_users(200)
