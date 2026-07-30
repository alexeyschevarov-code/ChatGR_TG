import tempfile
from pathlib import Path

from chatgr_core.repositories.db import get_connection, init_db
from chatgr_core.repositories.users import UserRepository
from chatgr_core.services.dialog_service import DialogService


def test_save_and_leaderboard():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "t.db"
        init_db(db)
        conn = get_connection(db)
        repo = UserRepository(conn)
        svc = DialogService(repo)
        svc.process_text("111", "привет")
        svc.process_text("222", "космос")
        top = repo.leaderboard(10)
        assert len(top) >= 1
        assert all("xp" in p for p in top)
        stats = repo.stats()
        assert stats["users"] >= 2
        assert stats["messages"] >= 2
        conn.close()


def test_ban():
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "t.db"
        init_db(db)
        conn = get_connection(db)
        repo = UserRepository(conn)
        svc = DialogService(repo)
        repo.set_banned("999", True)
        r = svc.process_text("999", "привет")
        assert "заблокирован" in r.text.lower()
        conn.close()
