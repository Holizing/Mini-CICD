from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class DeployStartRequest(BaseModel):
    build_id: int
    project_id: int
    project_name: str
    branch: str
    server_ip: str
    server_user: str = Field(default="root")
    server_password: Optional[str] = None
    server_ssh_key: Optional[str] = None
    deploy_path: str
    service_name: str


class DeployResponse(BaseModel):
    id: int
    build_id: int
    project_id: int
    project_name: str
    branch: str
    server_ip: str
    server_user: str
    deploy_path: str
    service_name: str
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    duration: Optional[int]
    log_path: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True


class DeployHistoryResponse(BaseModel):
    deploys: list[DeployResponse]
    total: int
