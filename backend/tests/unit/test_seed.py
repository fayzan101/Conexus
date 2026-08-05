from app.bootstrap import seed_dev_users
from app.config import Settings
from app.db.models import Role, User
from app.db.session import Base


def test_seed_dev_users(db, test_settings: Settings):
    seed_dev_users(db, test_settings)
    admin = db.query(User).filter(User.email == test_settings.dev_admin_email).first()
    user = db.query(User).filter(User.email == test_settings.dev_user_email).first()
    assert admin is not None
    assert admin.role == Role.admin
    assert user is not None
    assert user.role == Role.employee


def test_sqlite_schema_create(db_engine):
    tables = set(Base.metadata.tables)
    assert "users" in tables
    assert "documents" in tables
    assert "chat_messages" in tables
