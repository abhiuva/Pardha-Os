from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ProjectScanRequest(BaseModel):
    project_path: str = Field(..., min_length=1)
    business_id: Optional[str] = None
    business_name: Optional[str] = None


class LargeModule(BaseModel):
    path: str
    lines: int


class ProjectAnalysis(BaseModel):
    folder_structure: List[str]
    file_count: int
    file_counts_by_extension: Dict[str, int]
    languages: Dict[str, int]
    manifests: List[str]
    has_readme: bool
    has_tests: bool
    has_docker: bool
    missing_documentation: List[str]
    missing_tests: List[str]
    large_modules: List[LargeModule]


class Project(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: str
    business_id: Optional[str] = None
    project_name: str
    project_path: str
    language: str
    framework: str
    repository_summary: str
    analysis: ProjectAnalysis
    last_scanned: datetime
