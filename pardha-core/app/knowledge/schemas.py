from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


KnowledgeCategory = Literal[
    "company",
    "product",
    "project",
    "roadmap",
    "prd",
    "sop",
    "meeting_notes",
    "customer_feedback",
]


class KnowledgeCreate(BaseModel):
    business_id: Optional[str] = None
    business_name: str = Field(..., min_length=1)
    category: KnowledgeCategory
    title: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    source: str = Field(..., min_length=1)
    source_uri: Optional[str] = None
    document_metadata: Dict[str, Any] = Field(default_factory=dict)


class Knowledge(KnowledgeCreate):
    model_config = ConfigDict(from_attributes=True)

    knowledge_id: UUID
    created_at: datetime
    embedding_model: Optional[str] = None
    embedding_reference: Optional[str] = None


class KnowledgeUploadItem(BaseModel):
    filename: str
    status: str
    message: str
    knowledge_id: Optional[UUID] = None
    import_id: Optional[str] = None
    duplicate: bool = False


class KnowledgeUploadResult(BaseModel):
    business_id: str
    business_name: str
    uploaded: int
    duplicates: int
    failed: int
    items: List[KnowledgeUploadItem]


class KnowledgeDeleteResult(BaseModel):
    knowledge_id: UUID
    deleted: bool


class KnowledgeSourceSummary(BaseModel):
    source: str
    source_uri: Optional[str] = None
    version: Optional[str] = None
    category: str
    title: str


class KnowledgeSummary(BaseModel):
    business_id: str
    business_name: str
    total_records: int
    categories: Dict[str, int] = Field(default_factory=dict)
    sources: List[KnowledgeSourceSummary] = Field(default_factory=list)
    expected_sources: List[str] = Field(default_factory=list)
    missing_expected_sources: List[str] = Field(default_factory=list)
    context_ready: bool
    generated_at: datetime
