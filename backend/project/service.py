from typing import Optional

from sqlalchemy.orm import Session

from backend.project.models import Project
from backend.project.schemas import ProjectCreate, ProjectUpdate


class ProjectService:
    def __init__(self, db: Session):
        self.db = db

    def create_project(self, data: ProjectCreate) -> Project:
        project = Project(**data.model_dump())
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_project(self, project_id: int) -> Optional[Project]:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def get_projects(
        self,
        limit: int = 50,
        offset: int = 0,
        project_status: Optional[str] = None,
    ) -> tuple[list[Project], int]:
        query = self.db.query(Project)
        if project_status:
            query = query.filter(Project.status == project_status)
        total = query.count()
        projects = query.order_by(Project.id.desc()).offset(offset).limit(limit).all()
        return projects, total

    def update_project(self, project_id: int, data: ProjectUpdate) -> Optional[Project]:
        project = self.get_project(project_id)
        if not project:
            return None

        updates = data.model_dump(exclude_unset=True)
        for key, value in updates.items():
            setattr(project, key, value)

        self.db.commit()
        self.db.refresh(project)
        return project

    def delete_project(self, project_id: int) -> bool:
        project = self.get_project(project_id)
        if not project:
            return False

        self.db.delete(project)
        self.db.commit()
        return True
