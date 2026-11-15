from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile, status

from app.knowledge.schemas import Knowledge, KnowledgeCategory, KnowledgeCreate, KnowledgeDeleteResult, KnowledgeSummary, KnowledgeUploadResult
from app.knowledge.service import (
    create_knowledge,
    delete_knowledge,
    get_knowledge,
    get_knowledge_by_business,
    get_knowledge_summary,
    load_dp360_knowledge_context,
    search_knowledge,
    upload_knowledge_files,
)
from app.knowledge.importer import KnowledgeImport, get_knowledge_imports


router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/imports", response_model=list[KnowledgeImport])
def get_knowledge_imports_route():
    return get_knowledge_imports()


@router.get("/summary", response_model=KnowledgeSummary)
def get_knowledge_summary_route(
    business_name: Optional[str] = Query(default=None),
    business_id: Optional[str] = Query(default=None),
):
    return get_knowledge_summary(business_name=business_name, business_id=business_id)


@router.post("/dp360/load", response_model=KnowledgeSummary)
def load_dp360_knowledge_context_route():
    return load_dp360_knowledge_context()


@router.post("", response_model=Knowledge, status_code=status.HTTP_201_CREATED)
def create_knowledge_route(knowledge: KnowledgeCreate):
    return create_knowledge(knowledge)


@router.post("/upload", response_model=KnowledgeUploadResult, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_route(
    business_id: str = Form(...),
    business_name: str = Form(...),
    category: KnowledgeCategory = Form(default="company"),
    reimport: bool = Form(default=False),
    files: list[UploadFile] = File(...),
):
    payload = [(file.filename or "upload", await file.read()) for file in files]
    return upload_knowledge_files(
        business_id=business_id,
        business_name=business_name,
        category=category,
        reimport=reimport,
        files=payload,
    )


@router.get("", response_model=list[Knowledge])
def get_knowledge_route(
    business_name: Optional[str] = Query(default=None),
    business_id: Optional[str] = Query(default=None),
    category: Optional[KnowledgeCategory] = Query(default=None),
):
    return get_knowledge(business_name=business_name, business_id=business_id, category=category)


@router.get("/search", response_model=list[Knowledge])
def search_knowledge_route(
    query: str = Query(default=""),
    business_name: Optional[str] = Query(default=None),
    business_id: Optional[str] = Query(default=None),
    category: Optional[KnowledgeCategory] = Query(default=None),
):
    return search_knowledge(query=query, business_name=business_name, business_id=business_id, category=category)


@router.get("/business/{business_name}", response_model=list[Knowledge])
def get_knowledge_by_business_route(
    business_name: str,
    category: Optional[KnowledgeCategory] = Query(default=None),
):
    return get_knowledge_by_business(business_name=business_name, category=category)


@router.delete("/{knowledge_id}", response_model=KnowledgeDeleteResult)
def delete_knowledge_route(knowledge_id: str):
    try:
        return delete_knowledge(knowledge_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
