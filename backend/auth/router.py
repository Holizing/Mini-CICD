from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.auth import service
from backend.auth.dependencies import get_current_admin
from backend.auth.models import AdminUser
from backend.auth.schemas import AdminResponse, TokenResponse
from backend.auth.security import create_access_token
from backend.common.database import get_db


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
):
    admin = service.authenticate_admin(db, form_data.username, form_data.password)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, expires_in = create_access_token(admin.id, admin.username)
    return TokenResponse(
        access_token=access_token,
        expires_in=expires_in,
        user=admin,
    )


@router.get("/me", response_model=AdminResponse)
async def read_current_admin(
    current_admin: Annotated[AdminUser, Depends(get_current_admin)],
):
    return current_admin
