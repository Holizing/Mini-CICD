from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.sql import func
from backend.common.database import Base


class Build(Base):
    __tablename__ = "builds"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, nullable=False, index=True)
    project_name = Column(String(255), nullable=False)
    branch = Column(String(255), nullable=False)
    commit_hash = Column(String(255), nullable=True)
    status = Column(String(50), nullable=False, default="running")  # running, success, failed
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration = Column(Integer, nullable=True)  # in seconds
    log_path = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
