from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.db.models import Project
from app.deps import CurrentUser, DbSession
from app.schemas import ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
def list_projects(db: DbSession, user: CurrentUser):
    return (
        db.query(Project)
        .filter(Project.tenant_id == user.tenant_id)
        .order_by(Project.created_at.desc())
        .limit(100)
        .all()
    )


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: DbSession, user: CurrentUser):
    if (
        db.query(Project)
        .filter(Project.tenant_id == user.tenant_id, Project.name == payload.name)
        .first()
    ):
        raise HTTPException(status_code=400, detail="Project name already exists")
    project = Project(name=payload.name, description=payload.description, tenant_id=user.tenant_id)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: UUID, db: DbSession, user: CurrentUser):
    project = db.get(Project, project_id)
    if not project or project.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(project_id: UUID, payload: ProjectUpdate, db: DbSession, user: CurrentUser):
    project = db.get(Project, project_id)
    if not project or project.tenant_id != user.tenant_id:
        raise HTTPException(status_code=404, detail="Project not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project
