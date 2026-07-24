from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.auth.dependencies import get_current_admin
from backend.common.database import get_db
from backend.settings import service
from backend.settings.schemas import SettingsResponse, SettingsUpdate


router = APIRouter(
    prefix="/settings",
    tags=["settings"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("", response_model=SettingsResponse)
async def read_settings(db: Session = Depends(get_db)):
    return service.get_settings(db)


@router.put("", response_model=SettingsResponse)
async def save_settings(
    settings_data: SettingsUpdate,
    db: Session = Depends(get_db),
):
    return service.update_settings(db, settings_data)


@router.post("/reset", response_model=SettingsResponse)
async def restore_default_settings(db: Session = Depends(get_db)):
    return service.reset_settings(db)
