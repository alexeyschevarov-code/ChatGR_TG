import tempfile
from pathlib import Path

from chatgr_core.core.dialog import DialogEngine
from chatgr_core.core.changelog import format_changelog
from chatgr_core.core.facts import format_daily_fact
from chatgr_core.repositories.db import get_connection, init_db, verify_backup, backup_db
from chatgr_core.repositories.users import UserRepository
from chatgr_core.services.dialog_service import DialogService


def test_onboarding_flow():
    eng = DialogEngine()
    state = {"onboarding_step": 1, "character": "обычный", "recent_msgs": [], "topic_counts": {}}
    r = eng.handle("меня зовут Лёша", state=state, profile={})
    assert r.state["onboarding_step"] == 2
    assert r.state["name"] == "Лёша"
    r2 = eng.handle("квесты", state=r.state, profile=r.profile)
    assert r2.state["onboarding_step"] == 3
    r3 = eng.handle("викторина", state=r2.state, profile=r2.profile)
    assert r3.state["onboarding_step"] == 0
    assert r3.profile.get("onboarding_done")


def test_changelog():
    t = format_changelog()
    assert "1.0.0" in t or "нового" in t.lower()


def test_fact():
    t = format_daily_fact("космос")
    assert "Факт" in t


def test_export_and_backup():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "t.db"
        init_db(db)
        conn = get_connection(db)
        repo = UserRepository(conn)
        svc = DialogService(repo)
        svc.process_text("42", "привет")
        data = svc.build_export("42")
        assert "xp" in data
        assert "42" in data
        b = backup_db(db)
        assert b and b.exists()
        assert verify_backup(b)
        conn.close()
