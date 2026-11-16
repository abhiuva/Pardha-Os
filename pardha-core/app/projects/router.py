from fastapi import APIRouter, HTTPException, status

from app.projects.schemas import Project, ProjectScanRequest
from app.projects.service import get_project, get_projects, scan_project


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/scan", response_model=Project, status_code=status.HTTP_201_CREATED)
def scan_project_route(request: ProjectScanRequest):
    try:
        return scan_project(request.project_path, business_id=request.business_id, business_name=request.business_name)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("", response_model=list[Project])
def get_projects_route(business_id: str | None = None):
    return get_projects(business_id=business_id)


@router.get("/{project_id}", response_model=Project)
def get_project_route(project_id: str, business_id: str | None = None):
    project = get_project(project_id, business_id=business_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found.")
    return project
