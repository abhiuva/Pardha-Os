from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from uuid import uuid4

from app.db import SessionLocal
from app.db.models import Project as ProjectModel
from app.projects.schemas import LargeModule, Project, ProjectAnalysis


IGNORED_DIRECTORIES = {
    ".git",
    ".idea",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".vite",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "venv",
}
LANGUAGE_BY_EXTENSION = {
    ".c": "C",
    ".cpp": "C++",
    ".cs": "C#",
    ".css": "CSS",
    ".go": "Go",
    ".html": "HTML",
    ".java": "Java",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".kt": "Kotlin",
    ".php": "PHP",
    ".py": "Python",
    ".rb": "Ruby",
    ".rs": "Rust",
    ".swift": "Swift",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
}
TEXT_EXTENSIONS = set(LANGUAGE_BY_EXTENSION) | {".md", ".txt", ".toml", ".yaml", ".yml"}
LARGE_MODULE_LINES = 500


def _walk_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if any(part in IGNORED_DIRECTORIES for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            yield path


def _folder_structure(root: Path) -> List[str]:
    folders = []
    for path in root.iterdir():
        if path.name not in IGNORED_DIRECTORIES and path.is_dir():
            folders.append(f"{path.name}/")
    return sorted(folders)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def _detect_frameworks(root: Path) -> List[str]:
    frameworks: set[str] = set()
    node_frameworks = {
        "react": "React",
        "next": "Next.js",
        "vue": "Vue",
        "@angular/core": "Angular",
        "express": "Express",
        "vite": "Vite",
        "svelte": "Svelte",
    }
    requirements = []
    for path in _walk_files(root):
        if path.name == "package.json":
            package = _read_json(path)
            node_dependencies = {
                **package.get("dependencies", {}),
                **package.get("devDependencies", {}),
            }
            frameworks.update(
                name for dependency, name in node_frameworks.items() if dependency in node_dependencies
            )
        if path.name == "requirements.txt":
            try:
                requirements.append(path.read_text().lower())
            except (OSError, UnicodeDecodeError):
                pass
    requirements_text = " ".join(requirements)
    python_frameworks = {
        "fastapi": "FastAPI",
        "django": "Django",
        "flask": "Flask",
        "sqlalchemy": "SQLAlchemy",
    }
    frameworks.update(
        name for dependency, name in python_frameworks.items() if dependency in requirements_text
    )
    return sorted(frameworks)


def _manifest_paths(root: Path, files: List[Path]) -> List[str]:
    manifests = []
    for path in files:
        normalized_name = path.name.lower()
        if normalized_name in {"package.json", "requirements.txt", "pyproject.toml", "dockerfile"} or normalized_name.startswith(
            "docker-compose"
        ):
            manifests.append(str(path.relative_to(root)))
    return sorted(manifests)


def _analyze_path(root: Path) -> ProjectAnalysis:
    files = list(_walk_files(root))
    extension_counts = Counter(path.suffix.lower() or "[no extension]" for path in files)
    languages = Counter(
        LANGUAGE_BY_EXTENSION[path.suffix.lower()]
        for path in files
        if path.suffix.lower() in LANGUAGE_BY_EXTENSION
    )
    manifests = _manifest_paths(root, files)
    has_readme = any(path.name.lower().startswith("readme") for path in files)
    has_tests = any(
        "test" in part.lower()
        for path in files
        for part in path.relative_to(root).parts
    )
    has_docker = any(
        path.name.lower() == "dockerfile" or path.name.lower().startswith("docker-compose")
        for path in files
    )

    large_modules: List[LargeModule] = []
    for path in files:
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        try:
            with path.open(errors="ignore") as source:
                lines = sum(1 for _ in source)
        except OSError:
            continue
        if lines >= LARGE_MODULE_LINES:
            large_modules.append(LargeModule(path=str(path.relative_to(root)), lines=lines))

    missing_documentation = []
    if not has_readme:
        missing_documentation.append("README")
    if not any("docs" == part.lower() for path in files for part in path.relative_to(root).parts):
        missing_documentation.append("docs directory")
    missing_tests = [] if has_tests else ["No test files or test directories detected."]

    return ProjectAnalysis(
        folder_structure=_folder_structure(root),
        file_count=len(files),
        file_counts_by_extension=dict(sorted(extension_counts.items())),
        languages=dict(sorted(languages.items(), key=lambda item: (-item[1], item[0]))),
        manifests=manifests,
        has_readme=has_readme,
        has_tests=has_tests,
        has_docker=has_docker,
        missing_documentation=missing_documentation,
        missing_tests=missing_tests,
        large_modules=sorted(large_modules, key=lambda item: (-item.lines, item.path))[:20],
    )


def _summary(project_name: str, analysis: ProjectAnalysis, frameworks: List[str]) -> str:
    language = next(iter(analysis.languages), "Unknown")
    stack = ", ".join(frameworks) if frameworks else "no framework detected"
    return (
        f"{project_name} is primarily a {language} project using {stack}. "
        f"It contains {analysis.file_count} files across {len(analysis.folder_structure)} top-level directories. "
        f"Tests are {'present' if analysis.has_tests else 'not detected'} and "
        f"documentation is {'present' if analysis.has_readme else 'missing'}."
    )


def _row_to_project(row: ProjectModel) -> Project:
    return Project(
        project_id=row.project_id,
        project_name=row.project_name,
        project_path=row.project_path,
        language=row.language,
        framework=row.framework,
        repository_summary=row.repository_summary,
        analysis=ProjectAnalysis.model_validate(row.analysis),
        last_scanned=row.last_scanned,
    )


def scan_project(project_path: str, business_id: Optional[str] = None, business_name: Optional[str] = None) -> Project:
    from app.business.service import resolve_business

    business = resolve_business(business_id=business_id, business_name=business_name, text=project_path)
    root = Path(project_path).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        raise ValueError(f"Project directory does not exist: {root}")

    analysis = _analyze_path(root)
    frameworks = _detect_frameworks(root)
    language = next(iter(analysis.languages), "Unknown")
    framework = ", ".join(frameworks) if frameworks else "Unknown"
    now = datetime.now(timezone.utc)

    with SessionLocal() as session:
        row = session.query(ProjectModel).filter(ProjectModel.project_path == str(root)).one_or_none()
        if row is None:
            row = ProjectModel(project_id=str(uuid4()), project_path=str(root))
            session.add(row)
        row.business_id = business.business_id
        row.project_name = root.name
        row.language = language
        row.framework = framework
        row.repository_summary = _summary(root.name, analysis, frameworks)
        row.analysis = analysis.model_dump(mode="json")
        row.last_scanned = now
        session.commit()
        session.refresh(row)
        return _row_to_project(row)


def get_projects(business_id: Optional[str] = None) -> List[Project]:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
    with SessionLocal() as session:
        rows = (
            session.query(ProjectModel)
            .filter(ProjectModel.business_id == business_id)
            .order_by(ProjectModel.project_name, ProjectModel.project_id)
            .all()
        )
        return [_row_to_project(row) for row in rows]


def get_project(project_id: str, business_id: Optional[str] = None) -> Optional[Project]:
    if business_id is None:
        from app.business.service import get_active_business

        business_id = get_active_business().business_id
    with SessionLocal() as session:
        row = session.get(ProjectModel, project_id)
        if row is not None and row.business_id != business_id:
            return None
        return _row_to_project(row) if row is not None else None


def analyze_project(project_id: str) -> Optional[ProjectAnalysis]:
    project = get_project(project_id)
    return project.analysis if project is not None else None
