from sqlalchemy.orm import Session

from backend.auth.models import AdminUser
from backend.auth.security import DUMMY_PASSWORD_HASH, hash_password, verify_password


MIN_USERNAME_LENGTH = 3
MAX_USERNAME_LENGTH = 100
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 128


def normalize_username(username: str) -> str:
    return username.strip().lower()


def validate_admin_credentials(username: str, password: str) -> tuple[str, str]:
    normalized_username = normalize_username(username)

    if len(normalized_username) < MIN_USERNAME_LENGTH or len(normalized_username) > MAX_USERNAME_LENGTH:
        raise ValueError("Username must contain between 3 and 100 characters")
    if any(character.isspace() for character in normalized_username):
        raise ValueError("Username cannot contain whitespace")
    if len(password) < MIN_PASSWORD_LENGTH or len(password) > MAX_PASSWORD_LENGTH:
        raise ValueError("Password must contain between 12 and 128 characters")

    return normalized_username, password


def get_admin_by_id(db: Session, admin_id: int) -> AdminUser | None:
    return db.query(AdminUser).filter(AdminUser.id == admin_id).first()


def authenticate_admin(db: Session, username: str, password: str) -> AdminUser | None:
    normalized_username = normalize_username(username)
    admin = db.query(AdminUser).filter(AdminUser.username == normalized_username).first()
    password_has_valid_length = 1 <= len(password) <= MAX_PASSWORD_LENGTH
    password_hash = (
        admin.password_hash
        if admin is not None and password_has_valid_length
        else DUMMY_PASSWORD_HASH
    )
    password_to_verify = password if password_has_valid_length else "mini-cicd-invalid-password"

    password_is_valid = verify_password(password_to_verify, password_hash)
    if admin is None or not password_has_valid_length or not password_is_valid or not admin.is_active:
        return None

    return admin


def create_or_update_admin(db: Session, username: str, password: str) -> tuple[AdminUser, bool]:
    normalized_username, valid_password = validate_admin_credentials(username, password)
    admin = db.query(AdminUser).order_by(AdminUser.id.asc()).first()
    created = admin is None

    if admin is None:
        admin = AdminUser(
            username=normalized_username,
            password_hash=hash_password(valid_password),
            is_active=True,
        )
        db.add(admin)
    else:
        admin.username = normalized_username
        admin.password_hash = hash_password(valid_password)
        admin.is_active = True

    db.commit()
    db.refresh(admin)
    return admin, created
