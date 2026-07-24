from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from pwdlib import PasswordHash

from backend.auth.config import (
    JWT_ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    get_access_token_expire_minutes,
    get_jwt_secret,
)


password_hasher = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hasher.hash("mini-cicd-invalid-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(admin_id: int, username: str) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    expires_in = get_access_token_expire_minutes() * 60
    expires_at = now + timedelta(seconds=expires_in)
    payload = {
        "sub": f"admin:{admin_id}",
        "username": username,
        "type": "access",
        "iat": now,
        "exp": expires_at,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    token = jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)
    return token, expires_in


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(
        token,
        get_jwt_secret(),
        algorithms=[JWT_ALGORITHM],
        audience=JWT_AUDIENCE,
        issuer=JWT_ISSUER,
        options={"require": ["sub", "type", "iat", "exp"]},
    )
