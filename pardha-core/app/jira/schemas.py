from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class JiraProject(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    jira_project_id: str
    project_key: str
    jira_url: str
    name: str
    email: str
    status: str
    last_synced_at: Optional[datetime]
    metadata_json: Dict[str, Any] = Field(alias="metadata")
    created_at: datetime
    updated_at: datetime


class JiraIssue(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    jira_issue_id: str
    jira_issue_key: str
    project_key: str
    issue_type: str
    source_type: str
    source_id: str
    parent_jira_issue_key: Optional[str]
    summary: str
    description: Optional[str]
    status: str
    url: Optional[str]
    raw: Dict[str, Any]
    synced_at: datetime
    updated_at: datetime


class JiraSyncHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    jira_sync_id: str
    project_key: str
    objective_id: Optional[str]
    status: str
    action: str
    summary: str
    issue_count: int
    error: Optional[str]
    payload: Dict[str, Any]
    started_at: datetime
    completed_at: datetime


class JiraSyncRequest(BaseModel):
    objective_id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    business_name: Optional[str] = None
    priority: str = "medium"
    dry_run: bool = False


class JiraStatus(BaseModel):
    connected: bool
    project_count: int
    issue_count: int
    configured: bool
    enabled: bool
    project_key: Optional[str]
    jira_url: Optional[str]
    epic_count: int
    story_count: int
    last_sync: Optional[datetime]
    message: str


class JiraSyncResult(BaseModel):
    status: str
    project_key: str
    objective_id: Optional[str]
    epic: Optional[JiraIssue]
    stories: List[JiraIssue]
    technical_stories: List[JiraIssue]
    history: JiraSyncHistory
