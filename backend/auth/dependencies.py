from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from backend.auth import service
from backend.auth.models import AdminUser
from backend.auth.security import decode_access_token
from backend.common.database import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def authentication_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_admin(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> AdminUser:
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub", "")
        token_type = payload.get("type")
        if token_type != "access" or not subject.startswith("admin:"):
            raise authentication_error()
        admin_id = int(subject.removeprefix("admin:"))
    except (jwt.InvalidTokenError, TypeError, ValueError):
        raise authentication_error() from None

    admin = service.get_admin_by_id(db, admin_id)
    if admin is None or not admin.is_active:
        raise authentication_error()

    return admin
