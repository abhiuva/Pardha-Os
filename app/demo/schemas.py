from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field

from app.business.schemas import Business
from app.collaboration.schemas import ObjectiveWorkflowResult


class DemoSeedResult(BaseModel):
    businesses: List[Business]
    objectives_created: int
    projects_created: int
    knowledge_created: int
    jira_issues_created: int


class FounderCopilotRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    business_name: str | None = None
    priority: str = "high"


class FounderCopilotResponse(BaseModel):
    prompt: str
    business_name: str
    ceo_strategy: List[str]
    pm_roadmap: List[str]
    cto_tasks: List[str]
    workflow: ObjectiveWorkflowResult
