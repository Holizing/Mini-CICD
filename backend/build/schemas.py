from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class BuildStartRequest(BaseModel):
    project_id: int
    project_name: str
    branch: str
    git_url: str


class BuildResponse(BaseModel):
    id: int
    project_id: int
    project_name: str
    branch: str
    commit_hash: Optional[str]
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[int]
    log_path: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class BuildStatusResponse(BaseModel):
    build_id: int
    status: str
    progress: str


class BuildHistoryResponse(BaseModel):
    builds: list[BuildResponse]
    total: int
