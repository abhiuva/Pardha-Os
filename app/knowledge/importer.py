from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import IntegrityError
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver

from app.db import SessionLocal
from app.db.models import Event as EventModel
from app.db.models import Knowledge as KnowledgeModel
from app.db.models import KnowledgeImport as KnowledgeImportModel
from app.knowledge.schemas import KnowledgeCategory


logger = logging.getLogger(__name__)
WATCHED_BUSINESS_FOLDERS = ("uva", "dp360", "eatontime", "trevia")
NOTIFIED_AGENTS = ("ceo", "cto", "pm")
CATEGORY_ALIASES: Dict[str, KnowledgeCategory] = {
    "architecture": "project",
    "company_profile": "company",
    "customer_problems": "customer_feedback",
}
VALID_CATEGORIES = {
    "company",
    "product",
    "project",
    "roadmap",
    "prd",
    "sop",
    "meeting_notes",
    "customer_feedback",
}


class KnowledgeImportDocument(BaseModel):
    business_name: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    content: Any
    tags: List[str] = Field(default_factory=list)
    source: str = Field(..., min_length=1)
    version: Optional[str] = None


class KnowledgeImport(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    import_id: str
    file_path: str
    file_hash: str
    business_id: str | None = None
    business_name: str
    knowledge_id: UUID
    imported_at: datetime


def knowledge_root() -> Path:
    configured = os.getenv("PARDHA_KNOWLEDGE_ROOT")
    return Path(configured).expanduser().resolve() if configured else Path(__file__).resolve().parents[3] / "knowledge"


def _normalized_category(category: str) -> KnowledgeCategory:
    normalized = category.strip().lower()
    mapped = CATEGORY_ALIASES.get(normalized, normalized)
    if mapped not in VALID_CATEGORIES:
        raise ValueError(f"Unsupported knowledge category: {category}")
    return mapped  # type: ignore[return-value]


def _content_text(content: Any) -> str:
    if isinstance(content, str):
        if not content.strip():
            raise ValueError("Knowledge content must not be empty.")
        return content.strip()
    return json.dumps(content, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _is_watched_file(file_path: Path, root: Path) -> bool:
    try:
        relative = file_path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return (
        file_path.suffix.lower() == ".json"
        and len(relative.parts) == 2
        and relative.parts[0].lower() in WATCHED_BUSINESS_FOLDERS
    )


def import_knowledge_file(file_path: Path | str, root: Optional[Path] = None) -> Optional[KnowledgeImport]:
    path = Path(file_path).resolve()
    root = (root or knowledge_root()).resolve()
    if not _is_watched_file(path, root):
        return None

    raw = path.read_bytes()
    file_hash = hashlib.sha256(raw).hexdigest()
    document = KnowledgeImportDocument.model_validate_json(raw)
    relative = path.relative_to(root)
    folder_name = relative.parts[0].lower()
    from app.business.service import resolve_business_from_folder

    business = resolve_business_from_folder(folder_name)
    category = _normalized_category(document.category)
    content = _content_text(document.content)
    relative_path = str(relative)
    now = datetime.now(timezone.utc)
    knowledge_id = uuid4()
    import_id = str(uuid4())
    metadata = {
        "imported_file": relative_path,
        "original_category": document.category,
    }
    if document.version:
        metadata["version"] = document.version

    with SessionLocal() as session:
        existing = (
            session.query(KnowledgeImportModel)
            .filter(KnowledgeImportModel.file_path == relative_path)
            .first()
        )
        if existing is not None:
            return None

        session.add(
            KnowledgeModel(
                knowledge_id=knowledge_id,
                business_id=business.business_id,
                business_name=business.business_name,
                category=category,
                title=document.title.strip(),
                content=content,
                tags=document.tags,
                source=document.source.strip(),
                source_uri=relative_path,
                document_metadata_json=metadata,
            )
        )
        session.add(
            KnowledgeImportModel(
                import_id=import_id,
                file_path=relative_path,
                file_hash=file_hash,
                business_id=business.business_id,
                business_name=business.business_name,
                knowledge_id=knowledge_id,
                imported_at=now,
            )
        )
        payload = {
            "import_id": import_id,
            "knowledge_id": str(knowledge_id),
            "business_id": business.business_id,
            "business_name": business.business_name,
            "category": category,
            "title": document.title.strip(),
            "file_path": relative_path,
        }
        for target_agent in NOTIFIED_AGENTS:
            session.add(
                EventModel(
                    event_id=str(uuid4()),
                    business_id=business.business_id,
                    source_agent="knowledge-import-agent",
                    target_agent=target_agent,
                    event_type="KNOWLEDGE_ADDED",
                    payload=payload,
                    timestamp=now,
                )
            )
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            return None

        row = session.get(KnowledgeImportModel, import_id)
        return KnowledgeImport.model_validate(row)


def scan_knowledge_folders(root: Optional[Path] = None) -> List[KnowledgeImport]:
    root = (root or knowledge_root()).resolve()
    imported: List[KnowledgeImport] = []
    for folder_name in WATCHED_BUSINESS_FOLDERS:
        folder = root / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        for file_path in sorted(folder.glob("*.json")):
            try:
                result = import_knowledge_file(file_path, root)
                if result is not None:
                    imported.append(result)
            except Exception:
                logger.exception("Knowledge import failed for %s", file_path)
    return imported


def get_knowledge_imports() -> List[KnowledgeImport]:
    with SessionLocal() as session:
        rows = (
            session.query(KnowledgeImportModel)
            .order_by(KnowledgeImportModel.imported_at.desc(), KnowledgeImportModel.import_id.desc())
            .all()
        )
        return [KnowledgeImport.model_validate(row) for row in rows]


def clear_knowledge_imports() -> None:
    with SessionLocal() as session:
        session.query(KnowledgeImportModel).delete()
        session.commit()


class _KnowledgeFileHandler(FileSystemEventHandler):
    def __init__(self, root: Path):
        self.root = root

    def _import(self, file_path: str) -> None:
        try:
            import_knowledge_file(file_path, self.root)
        except Exception:
            logger.exception("Knowledge import failed for %s", file_path)

    def on_created(self, event) -> None:
        if not event.is_directory:
            self._import(event.src_path)

    def on_moved(self, event) -> None:
        if not event.is_directory:
            self._import(event.dest_path)

    def on_modified(self, event) -> None:
        if not event.is_directory:
            self._import(event.src_path)


_observer: Optional[PollingObserver] = None
_observer_lock = Lock()


def start_knowledge_watcher() -> None:
    global _observer
    enabled = os.getenv("PARDHA_KNOWLEDGE_WATCHER_ENABLED", "true").lower() not in {"0", "false", "no"}
    if not enabled:
        return

    with _observer_lock:
        if _observer is not None and _observer.is_alive():
            return
        root = knowledge_root()
        scan_knowledge_folders(root)
        observer = PollingObserver(timeout=1)
        observer.schedule(_KnowledgeFileHandler(root), str(root), recursive=True)
        observer.start()
        _observer = observer


def stop_knowledge_watcher() -> None:
    global _observer
    with _observer_lock:
        if _observer is not None:
            _observer.stop()
            _observer.join(timeout=5)
        _observer = None


def knowledge_watcher_status() -> str:
    if _observer is None:
        return "stopped"
    return "running" if _observer.is_alive() else "stopped"
