from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.jira.client import JiraConfigurationError
from app.jira.schemas import JiraIssue, JiraProject, JiraStatus, JiraSyncRequest, JiraSyncResult
from app.jira.service import get_issues, get_projects, jira_status, sync_jira
from app.security.write_guard import ExternalWriteBlocked


router = APIRouter(prefix="/jira", tags=["jira"])


@router.get("/status", response_model=JiraStatus)
def jira_status_route():
    return jira_status()


@router.post("/sync", response_model=JiraSyncResult, status_code=status.HTTP_201_CREATED)
def sync_jira_route(request: JiraSyncRequest):
    try:
        return sync_jira(request)
    except ExternalWriteBlocked as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except JiraConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/issues", response_model=list[JiraIssue])
def get_jira_issues_route():
    return get_issues()


@router.get("/projects", response_model=list[JiraProject])
def get_jira_projects_route():
    return get_projects()
