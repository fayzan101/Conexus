from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Role, User
from app.deps import get_user_by_email, hash_password


def seed_dev_users(db: Session, settings: Settings) -> None:
    seeds = [
        (settings.dev_admin_email, settings.dev_admin_password, "Admin User", Role.admin),
        (settings.dev_user_email, settings.dev_user_password, "Employee User", Role.employee),
    ]
    for email, password, name, role in seeds:
        existing = get_user_by_email(db, email)
        if existing:
            continue
        db.add(
            User(
                email=email,
                full_name=name,
                hashed_password=hash_password(password),
                role=role,
                is_active=True,
            )
        )
    db.commit()
