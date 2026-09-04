import os

# --- 1. アプリインポート前に必要な環境変数を一括設定 ---
os.environ["EMAIL_USERNAME"] = "dummy_user@example.com"
os.environ["EMAIL_PASSWORD"] = "dummy_pass"
os.environ["IMAP_SERVER"] = "imap.example.com"
os.environ["INFO_LOG"] = "infoMsg.txt"

os.environ["MAIL_SERVER"] = "smtp.example.com"
os.environ["MAIL_USERNAME"] = "dummy_user"
os.environ["MAIL_PASSWORD"] = "dummy_pass"
os.environ["MAIL_PORT"] = "587"
os.environ["MAIL_DEFAULT_SENDER"] = "sender@example.com"

os.environ["DAILY_NOTE_DIR"] = "dummy_daily_dir"
os.environ["WEEKLY_NOTE_DIR"] = "dummy_weekly_dir"
os.environ["WEEKLY_NOTE_TEMPLATE"] = "dummy_template.md"

import pytest
from app import create_app

@pytest.fixture
def client(tmp_path):
    test_db = tmp_path / "test.db"

    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": f"sqlite:///{test_db}",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.test_client() as client:
        yield client
