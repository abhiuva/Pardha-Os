from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from io import BytesIO, StringIO
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from xml.etree import ElementTree

from pydantic import BaseModel
from sqlalchemy import func

from app.db import SessionLocal
from app.db.models import Event as EventModel
from app.db.models import Knowledge as KnowledgeModel
from app.db.models import KnowledgeImport as KnowledgeImportModel
from app.knowledge.schemas import Knowledge, KnowledgeCategory, KnowledgeCreate, KnowledgeDeleteResult, KnowledgeUploadItem, KnowledgeUploadResult


SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md", ".markdown", ".csv", ".json"}


def _model_to_dict(model: BaseModel | Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(model, dict):
        return model
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _row_to_knowledge(row: KnowledgeModel) -> Knowledge:
    return Knowledge(
        knowledge_id=row.knowledge_id,
        business_id=row.business_id,
        business_name=row.business_name,
        category=row.category,
        title=row.title,
        content=row.content,
        tags=row.tags or [],
        source=row.source,
        created_at=row.created_at,
        source_uri=row.source_uri,
        document_metadata=row.document_metadata_json or {},
        embedding_model=row.embedding_model,
        embedding_reference=row.embedding_reference,
    )


def _base_query(session, business_name: Optional[str], category: Optional[KnowledgeCategory]):
    query = session.query(KnowledgeModel)
    if business_name:
        query = query.filter(func.lower(KnowledgeModel.business_name) == business_name.strip().lower())
    if category:
        query = query.filter(KnowledgeModel.category == category)
    return query


def create_knowledge(knowledge_data: KnowledgeCreate | Dict[str, Any]) -> Knowledge:
    validated = KnowledgeCreate.model_validate(_model_to_dict(knowledge_data))
    payload = validated.model_dump()
    from app.business.service import resolve_business

    business = resolve_business(
        business_id=payload.get("business_id"),
        business_name=payload["business_name"],
        text=f"{payload['title']} {payload['content']}",
    )
    row = KnowledgeModel(
        knowledge_id=uuid4(),
        business_id=business.business_id,
        business_name=business.business_name,
        category=payload["category"],
        title=payload["title"].strip(),
        content=payload["content"].strip(),
        tags=payload["tags"],
        source=payload["source"].strip(),
        source_uri=payload["source_uri"],
        document_metadata_json=payload["document_metadata"],
    )

    with SessionLocal() as session:
        session.add(row)
        session.commit()
        session.refresh(row)
        return _row_to_knowledge(row)


def upload_knowledge_files(
    *,
    business_id: str,
    business_name: str,
    files: list[tuple[str, bytes]],
    category: KnowledgeCategory = "company",
    reimport: bool = False,
) -> KnowledgeUploadResult:
    from app.business.service import resolve_business

    business = resolve_business(business_id=business_id, business_name=business_name)
    items: list[KnowledgeUploadItem] = []
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        for filename, raw in files:
            suffix = _suffix(filename)
            if suffix not in SUPPORTED_UPLOAD_EXTENSIONS:
                items.append(KnowledgeUploadItem(filename=filename, status="failed", message=f"Unsupported file type: {suffix or 'unknown'}"))
                continue
            file_hash = hashlib.sha256(raw).hexdigest()
            existing = session.query(KnowledgeImportModel).filter(KnowledgeImportModel.file_hash == file_hash).one_or_none()
            if existing is not None and not reimport:
                items.append(
                    KnowledgeUploadItem(
                        filename=filename,
                        status="duplicate",
                        message="Duplicate file detected; existing knowledge retained.",
                        knowledge_id=existing.knowledge_id,
                        import_id=existing.import_id,
                        duplicate=True,
                    )
                )
                continue
            try:
                content = _extract_upload_text(filename, raw)
            except ValueError as exc:
                items.append(KnowledgeUploadItem(filename=filename, status="failed", message=str(exc)))
                continue
            knowledge_id = uuid4()
            import_id = str(uuid4())
            source_uri = f"upload://{business.business_name}/{filename}"
            metadata = {"filename": filename, "file_hash": file_hash, "upload_source": "knowledge-center", "file_type": suffix}
            row = KnowledgeModel(
                knowledge_id=knowledge_id,
                business_id=business.business_id,
                business_name=business.business_name,
                category=category,
                title=_title_from_filename(filename),
                content=content,
                tags=["ui-upload", suffix.lstrip(".")],
                source="knowledge-center",
                source_uri=source_uri,
                document_metadata_json=metadata,
            )
            session.add(row)
            session.add(
                KnowledgeImportModel(
                    import_id=import_id,
                    file_path=source_uri if not reimport else f"{source_uri}#{import_id}",
                    file_hash=file_hash if not reimport else hashlib.sha256(f"{file_hash}:{import_id}".encode()).hexdigest(),
                    business_id=business.business_id,
                    business_name=business.business_name,
                    knowledge_id=knowledge_id,
                    imported_at=now,
                )
            )
            payload = {"import_id": import_id, "knowledge_id": str(knowledge_id), "business_id": business.business_id, "business_name": business.business_name, "title": row.title, "file_path": source_uri}
            for target_agent in ("ceo", "cto", "pm"):
                session.add(EventModel(event_id=str(uuid4()), business_id=business.business_id, source_agent="knowledge-center", target_agent=target_agent, event_type="KNOWLEDGE_ADDED", payload=payload, timestamp=now))
            items.append(KnowledgeUploadItem(filename=filename, status="imported", message="Knowledge imported successfully.", knowledge_id=knowledge_id, import_id=import_id))
        session.commit()
    return KnowledgeUploadResult(
        business_id=business.business_id,
        business_name=business.business_name,
        uploaded=sum(1 for item in items if item.status == "imported"),
        duplicates=sum(1 for item in items if item.duplicate),
        failed=sum(1 for item in items if item.status == "failed"),
        items=items,
    )


def delete_knowledge(knowledge_id: str) -> KnowledgeDeleteResult:
    with SessionLocal() as session:
        row = session.get(KnowledgeModel, UUID(str(knowledge_id)))
        if row is None:
            raise ValueError("Knowledge not found.")
        session.query(KnowledgeImportModel).filter(KnowledgeImportModel.knowledge_id == row.knowledge_id).delete()
        session.delete(row)
        session.commit()
        return KnowledgeDeleteResult(knowledge_id=row.knowledge_id, deleted=True)


def get_knowledge(
    business_name: Optional[str] = None,
    business_id: Optional[str] = None,
    category: Optional[KnowledgeCategory] = None,
) -> List[Knowledge]:
    from app.business.service import get_active_business

    with SessionLocal() as session:
        query = session.query(KnowledgeModel)
        if business_id:
            query = query.filter(KnowledgeModel.business_id == business_id)
        elif business_name:
            query = query.filter(func.lower(KnowledgeModel.business_name) == business_name.strip().lower())
        else:
            query = query.filter(KnowledgeModel.business_id == get_active_business().business_id)
        if category:
            query = query.filter(KnowledgeModel.category == category)
        rows = query.order_by(KnowledgeModel.created_at.desc(), KnowledgeModel.knowledge_id.asc()).all()
        return [_row_to_knowledge(row) for row in rows]


def search_knowledge(
    query: str = "",
    business_name: Optional[str] = None,
    business_id: Optional[str] = None,
    category: Optional[KnowledgeCategory] = None,
) -> List[Knowledge]:
    normalized_query = query.strip().lower()
    rows = get_knowledge(business_name=business_name, business_id=business_id, category=category)
    if not normalized_query:
        return rows

    results: List[Knowledge] = []
    for item in rows:
        searchable = " ".join(
            [
                item.business_name,
                item.category,
                item.title,
                item.content,
                " ".join(item.tags),
                item.source,
                item.source_uri or "",
                " ".join(f"{key} {value}" for key, value in sorted(item.document_metadata.items())),
            ]
        ).lower()
        if normalized_query in searchable:
            results.append(item)
    return results


def get_knowledge_by_business(
    business_name: str,
    category: Optional[KnowledgeCategory] = None,
) -> List[Knowledge]:
    return get_knowledge(business_name=business_name, category=category)


def _suffix(filename: str) -> str:
    return "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def _title_from_filename(filename: str) -> str:
    base = filename.rsplit("/", 1)[-1].rsplit(".", 1)[0]
    return base.replace("_", " ").replace("-", " ").strip().title() or "Uploaded Knowledge"


def _extract_upload_text(filename: str, raw: bytes) -> str:
    if not raw:
        raise ValueError("File is empty.")
    suffix = _suffix(filename)
    if suffix == ".json":
        try:
            return json.dumps(json.loads(raw.decode("utf-8")), indent=2, sort_keys=True)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid JSON file.") from exc
    if suffix == ".csv":
        text = _decode_text(raw)
        rows = list(csv.reader(StringIO(text)))
        return "\n".join(", ".join(cell.strip() for cell in row) for row in rows[:250]).strip()
    if suffix in {".txt", ".md", ".markdown"}:
        return _decode_text(raw)
    if suffix == ".docx":
        return _extract_docx_text(raw)
    if suffix == ".pptx":
        return _extract_pptx_text(raw)
    if suffix == ".pdf":
        return _extract_pdf_text(raw)
    text = _decode_text(raw, fallback=True)
    if len(text.strip()) < 20:
        return f"Uploaded {suffix.upper().lstrip('.')} document: {filename}. Binary document stored for preview metadata; text extraction requires a production document parser."
    return text


def _decode_text(raw: bytes, fallback: bool = False) -> str:
    for encoding in ("utf-8", "utf-16", "latin-1"):
        try:
            text = raw.decode(encoding, errors="ignore").strip()
            if text:
                return text[:20000]
        except UnicodeDecodeError:
            continue
    if fallback:
        return ""
    raise ValueError("Unable to read file text.")


def _extract_docx_text(raw: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            document = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("Invalid DOCX file.") from exc
    text = _xml_text(document)
    if len(text) < 20:
        raise ValueError("DOCX text extraction produced no usable text.")
    return text[:20000]


def _extract_pptx_text(raw: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            slide_names = sorted(name for name in archive.namelist() if name.startswith("ppt/slides/slide") and name.endswith(".xml"))
            parts = [_xml_text(archive.read(name)) for name in slide_names[:80]]
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid PPTX file.") from exc
    text = "\n".join(part for part in parts if part).strip()
    if len(text) < 20:
        raise ValueError("PPTX text extraction produced no usable text.")
    return text[:20000]


def _extract_pdf_text(raw: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(raw))
        text = "\n".join((page.extract_text() or "") for page in reader.pages[:80]).strip()
        if text:
            return text[:20000]
    except Exception:
        pass
    text = _decode_text(raw, fallback=True)
    if len(text.strip()) < 20:
        raise ValueError("PDF text extraction requires a text-based PDF or pypdf support.")
    return text[:20000]


def _xml_text(raw_xml: bytes) -> str:
    root = ElementTree.fromstring(raw_xml)
    text_nodes = []
    for node in root.iter():
        if node.tag.endswith("}t") or node.tag.endswith("}instrText"):
            if node.text:
                text_nodes.append(node.text)
    return " ".join(part.strip() for part in text_nodes if part.strip()).strip()
