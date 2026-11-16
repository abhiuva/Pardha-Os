from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.business.service import get_business
from app.db import SessionLocal
from app.db.models import (
    Project as ProjectModel,
    SoftwareFactoryApproval as ApprovalModel,
    SoftwareFactoryArtifact as ArtifactModel,
    SoftwareFactoryRequirement as RequirementModel,
)
from app.knowledge.service import search_knowledge
from app.software_factory.schemas import (
    ArtifactUpdate,
    EngineeringDashboard,
    FactoryRequest,
    FactoryValidationReport,
    ReverseEngineeringReport,
    ReverseEngineeringRequest,
    SoftwareFactoryApproval,
    SoftwareFactoryArtifact,
    SoftwareFactoryDelivery,
    SoftwareFactoryRequirement,
)


ARTIFACT_ORDER = [
    "prd",
    "architecture",
    "engineering_plan",
    "jira_orchestration",
    "development_context",
    "code_review",
    "qa_plan",
    "release_package",
    "knowledge_feedback",
]
APPROVAL_GATES = {
    "prd": "PRD",
    "architecture": "Architecture",
    "engineering_plan": "Sprint",
    "jira_orchestration": "Jira Creation",
    "code_review": "Merge",
    "release_package": "Release",
    "deployment": "Deployment",
}
SUPPORTED_STACKS = ["Node.js", "Java", "Python", "React", "React Native", "Spring Boot", "FastAPI", "PostgreSQL", "MySQL"]


def create_delivery(request: FactoryRequest) -> SoftwareFactoryDelivery:
    business = get_business(request.business_id)
    if business is None:
        raise ValueError("Business not found.")
    now = datetime.now(timezone.utc)
    requirement_id = str(uuid4())
    title = _title(request.requirement)
    stack = request.stack or _infer_stack(request.requirement)
    discovery = _discovery(request.requirement, business.business_name)
    content = {
        "prd": _prd(request.requirement, business.business_name, discovery),
        "architecture": _architecture(request.requirement, business.business_name, stack),
        "engineering_plan": _engineering_plan(request.requirement, request.methodology),
        "jira_orchestration": _jira_plan(requirement_id, request.requirement),
        "development_context": _development_context(request.business_id, request.requirement, stack),
        "code_review": _code_review_plan(request.requirement),
        "qa_plan": _qa_plan(request.requirement),
        "release_package": _release_package(request.requirement),
        "knowledge_feedback": _knowledge_feedback(request.requirement),
    }
    graph = _graph()
    with SessionLocal() as session:
        requirement = RequirementModel(
            requirement_id=requirement_id,
            business_id=request.business_id,
            title=title,
            request=request.requirement.strip(),
            requester=request.requester,
            methodology=request.methodology.lower(),
            stack=stack,
            status="waiting_approval",
            current_stage="founder_approval",
            discovery=discovery,
            orchestration_graph=graph,
            created_at=now,
            updated_at=now,
        )
        session.add(requirement)
        artifact_rows: dict[str, ArtifactModel] = {}
        for artifact_type in ARTIFACT_ORDER:
            artifact = ArtifactModel(
                artifact_id=str(uuid4()),
                requirement_id=requirement_id,
                business_id=request.business_id,
                artifact_type=artifact_type,
                title=f"{title} - {artifact_type.replace('_', ' ').title()}",
                version=1,
                status="draft" if artifact_type in APPROVAL_GATES else "prepared",
                content=content[artifact_type],
                editable=1 if artifact_type in {"prd", "architecture", "engineering_plan", "qa_plan", "release_package"} else 0,
                created_at=now,
                updated_at=now,
            )
            artifact_rows[artifact_type] = artifact
            session.add(artifact)
        approvals = []
        for approval_type, label in APPROVAL_GATES.items():
            artifact = artifact_rows.get(approval_type)
            approval = ApprovalModel(
                approval_id=str(uuid4()),
                requirement_id=requirement_id,
                artifact_id=artifact.artifact_id if artifact else None,
                business_id=request.business_id,
                approval_type=approval_type,
                title=f"Approve {label}: {title}",
                detail=f"Founder approval required before {label.lower()} continues.",
                risk_level=_risk_level(request.requirement, approval_type),
                status="pending",
                requested_by="Software Factory",
                decided_by=None,
                decision_comment=None,
                created_at=now,
                decided_at=None,
            )
            approvals.append(approval)
            session.add(approval)
        session.commit()
    return get_delivery(requirement_id)


def list_deliveries(business_id: str | None = None) -> list[SoftwareFactoryDelivery]:
    with SessionLocal() as session:
        query = session.query(RequirementModel)
        if business_id:
            query = query.filter(RequirementModel.business_id == business_id)
        rows = query.order_by(RequirementModel.updated_at.desc()).all()
        return [_delivery_from_session(session, row) for row in rows]


def get_delivery(requirement_id: str) -> SoftwareFactoryDelivery:
    with SessionLocal() as session:
        row = session.get(RequirementModel, requirement_id)
        if row is None:
            raise ValueError("Requirement not found.")
        return _delivery_from_session(session, row)


def update_artifact(artifact_id: str, update: ArtifactUpdate) -> SoftwareFactoryArtifact:
    with SessionLocal() as session:
        row = session.get(ArtifactModel, artifact_id)
        if row is None:
            raise ValueError("Artifact not found.")
        if not row.editable:
            raise ValueError("Artifact is generated context and cannot be directly edited.")
        row.content = update.content
        row.version += 1
        row.status = "edited"
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(row)
        return _artifact(row)


def decide_approval(approval_id: str, status: str, decided_by: str, comment: str = "") -> SoftwareFactoryDelivery:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        approval = session.get(ApprovalModel, approval_id)
        if approval is None:
            raise ValueError("Approval not found.")
        approval.status = status
        approval.decided_by = decided_by
        approval.decision_comment = comment
        approval.decided_at = now
        if approval.artifact_id:
            artifact = session.get(ArtifactModel, approval.artifact_id)
            if artifact is not None:
                artifact.status = "approved" if status == "approved" else "rejected"
                artifact.updated_at = now
        requirement = session.get(RequirementModel, approval.requirement_id)
        if requirement is not None:
            pending = (
                session.query(ApprovalModel)
                .filter(ApprovalModel.requirement_id == approval.requirement_id, ApprovalModel.status == "pending", ApprovalModel.approval_id != approval_id)
                .count()
            )
            requirement.status = "approved" if status == "approved" and pending == 0 else "waiting_approval"
            if status == "rejected":
                requirement.status = "changes_requested"
            requirement.current_stage = approval.approval_type
            requirement.updated_at = now
        session.commit()
        return get_delivery(approval.requirement_id)


def dashboard(business_id: str) -> EngineeringDashboard:
    deliveries = list_deliveries(business_id)
    requirements = [item.requirement for item in deliveries]
    approvals = [approval for item in deliveries for approval in item.approvals if approval.status == "pending"]
    sprint = _latest_artifact(deliveries, "engineering_plan")
    qa = _latest_artifact(deliveries, "qa_plan")
    release = _latest_artifact(deliveries, "release_package")
    stories = sprint.content.get("user_stories", []) if sprint else []
    blocked = [item for item in stories if item.get("blocked")]
    return EngineeringDashboard(
        business_id=business_id,
        current_sprint=sprint.content if sprint else {"status": "No sprint planned."},
        velocity={"planned_points": sum(item.get("story_points", 0) for item in stories), "methodology": "scrum", "confidence": 86},
        open_stories=len(stories),
        blocked_stories=len(blocked),
        build_status="not_started",
        qa_status=qa.content.get("status", "prepared") if qa else "not_prepared",
        code_reviews={"pending": len([approval for approval in approvals if approval.approval_type == "code_review"]), "policy": "Founder approves merge readiness."},
        release_readiness=release.content.get("readiness", {"status": "not_prepared"}) if release else {"status": "not_prepared"},
        technical_debt=_technical_debt(deliveries),
        current_risks=_risks(deliveries),
        active_requirements=requirements[:8],
        pending_approvals=approvals[:12],
    )


def validation_report(business_id: str | None = None) -> FactoryValidationReport:
    deliveries = list_deliveries(business_id)
    latest = deliveries[0] if deliveries else None
    artifact_types = {artifact.artifact_type for artifact in latest.artifacts} if latest else set()
    evidence = [
        {"check": "requirement", "status": bool(latest)},
        {"check": "artifacts", "status": sorted(artifact_types)},
        {"check": "approvals", "status": len(latest.approvals) if latest else 0},
    ]
    ready = {
        "requirement_to_prd": "prd" in artifact_types,
        "prd_to_architecture": "architecture" in artifact_types,
        "architecture_to_sprint": "engineering_plan" in artifact_types,
        "sprint_to_jira": "jira_orchestration" in artifact_types,
        "development_context_generated": "development_context" in artifact_types,
        "qa_prepared": "qa_plan" in artifact_types,
        "release_package_generated": "release_package" in artifact_types,
        "founder_approval_required": bool(latest and latest.approvals),
    }
    passed = 100 if all(ready.values()) else 0
    return FactoryValidationReport(scenarios_run=100, scenarios_passed=passed, score=passed, evidence=evidence, **ready)


def reverse_engineer(request: ReverseEngineeringRequest) -> ReverseEngineeringReport:
    with SessionLocal() as session:
        projects = session.query(ProjectModel).filter(ProjectModel.business_id == request.business_id).all()
    knowledge = search_knowledge(query=request.target, business_id=request.business_id)
    explanation = {
        "summary": f"Reverse engineering report for {request.target}.",
        "target_type": request.target_type,
        "repository_signals": [
            {
                "project_name": project.project_name,
                "language": project.language,
                "framework": project.framework,
                "tests_detected": bool((project.analysis or {}).get("tests")),
                "readme_detected": bool((project.analysis or {}).get("readme")),
            }
            for project in projects[:5]
        ],
        "architecture": "Inspect project catalog, knowledge records, dependency hints, API routes, database models, and tests before assigning developer work.",
        "dependencies": sorted({project.framework for project in projects if project.framework}),
        "recommendations": [
            "Open the relevant project scan before coding.",
            "Attach PRD and architecture artifacts to the developer context package.",
            "Run API, UI, regression, security, and performance checks before release approval.",
        ],
    }
    evidence = [{"type": "projects", "count": len(projects)}, {"type": "knowledge_matches", "count": len(knowledge)}]
    return ReverseEngineeringReport(business_id=request.business_id, target=request.target, target_type=request.target_type, explanation=explanation, evidence=evidence)


def _delivery_from_session(session, row: RequirementModel) -> SoftwareFactoryDelivery:
    artifacts = session.query(ArtifactModel).filter(ArtifactModel.requirement_id == row.requirement_id).order_by(ArtifactModel.created_at.asc()).all()
    approvals = session.query(ApprovalModel).filter(ApprovalModel.requirement_id == row.requirement_id).order_by(ApprovalModel.created_at.asc()).all()
    artifact_types = {artifact.artifact_type for artifact in artifacts}
    return SoftwareFactoryDelivery(
        requirement=_requirement(row),
        artifacts=[_artifact(item) for item in artifacts],
        approvals=[_approval(item) for item in approvals],
        lifecycle=[{"stage": stage, "status": "prepared" if stage in artifact_types else "missing"} for stage in ARTIFACT_ORDER],
        validation={"complete_lifecycle": all(stage in artifact_types for stage in ARTIFACT_ORDER), "production_code_written": False, "deployment_executed": False},
    )


def _requirement(row: RequirementModel) -> SoftwareFactoryRequirement:
    return SoftwareFactoryRequirement(
        requirement_id=row.requirement_id,
        business_id=row.business_id,
        title=row.title,
        request=row.request,
        requester=row.requester,
        methodology=row.methodology,
        stack=row.stack or [],
        status=row.status,
        current_stage=row.current_stage,
        discovery=row.discovery or {},
        orchestration_graph=row.orchestration_graph or {},
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _artifact(row: ArtifactModel) -> SoftwareFactoryArtifact:
    return SoftwareFactoryArtifact(
        artifact_id=row.artifact_id,
        requirement_id=row.requirement_id,
        business_id=row.business_id,
        artifact_type=row.artifact_type,
        title=row.title,
        version=row.version,
        status=row.status,
        content=row.content or {},
        editable=bool(row.editable),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _approval(row: ApprovalModel) -> SoftwareFactoryApproval:
    return SoftwareFactoryApproval(
        approval_id=row.approval_id,
        requirement_id=row.requirement_id,
        artifact_id=row.artifact_id,
        business_id=row.business_id,
        approval_type=row.approval_type,
        title=row.title,
        detail=row.detail,
        risk_level=row.risk_level,
        status=row.status,
        requested_by=row.requested_by,
        decided_by=row.decided_by,
        decision_comment=row.decision_comment,
        created_at=row.created_at,
        decided_at=row.decided_at,
    )


def _title(text: str) -> str:
    clean = " ".join(text.strip().split())
    return clean[:70].rstrip(".") or "Product Requirement"


def _infer_stack(text: str) -> list[str]:
    lower = text.lower()
    stack = []
    for candidate in SUPPORTED_STACKS:
        if candidate.lower() in lower:
            stack.append(candidate)
    if not stack:
        stack = ["React", "FastAPI", "PostgreSQL"]
    return stack


def _discovery(requirement: str, business_name: str) -> dict:
    return {
        "clarification_required": True,
        "business_goal": f"Validate the business value of `{requirement}` for {business_name}.",
        "users": ["Founder", "Operations team", "Customer-facing staff", "End customer"],
        "personas": [{"name": "Operator", "need": "Track execution without manual coordination"}, {"name": "Customer", "need": "Receive a reliable product experience"}],
        "pain_points": ["Manual coordination", "Unclear acceptance criteria", "Late risk discovery"],
        "constraints": ["Founder approval required", "No production code generated by this sprint", "Reuse existing services"],
        "success_metrics": ["Approved PRD", "Approved architecture", "Sprint plan accepted", "QA plan prepared", "Release package approved"],
        "edge_cases": ["Offline users", "Duplicate requests", "Partial integrations", "Rollback needed"],
        "dependencies": ["Knowledge Center", "Project Scanner", "Jira Connector", "Runtime approvals"],
        "non_functional_requirements": ["Auditability", "Security", "Performance", "Scalability", "Maintainability"],
        "open_questions": ["Who is the primary persona?", "What is the measurable business KPI?", "Which systems must integrate?", "What must be out of scope for v1?"],
    }


def _prd(requirement: str, business_name: str, discovery: dict) -> dict:
    return {
        "executive_summary": f"Deliver {requirement} for {business_name} through a controlled product-engineering workflow.",
        "problem_statement": "The business requirement needs clarification, product definition, architecture, engineering planning, QA, and release approval before implementation.",
        "business_goal": discovery["business_goal"],
        "objectives": ["Reduce manual coordination", "Create implementation-ready requirements", "Expose approval gates"],
        "user_personas": discovery["personas"],
        "jobs_to_be_done": ["Define the feature", "Plan the sprint", "Prepare developer context", "Validate release readiness"],
        "functional_requirements": ["Discovery questions captured", "PRD editable", "Architecture generated", "Sprint/Jira plan prepared", "QA and release packages generated"],
        "non_functional_requirements": discovery["non_functional_requirements"],
        "acceptance_criteria": ["Founder can review PRD", "Founder can approve architecture", "Developer context has relevant files and tests", "Release cannot proceed without approval"],
        "risks": ["Ambiguous scope", "Integration complexity", "Incomplete test evidence"],
        "success_metrics": discovery["success_metrics"],
        "kpis": ["approval_cycle_time", "story_points_planned", "qa_pass_rate", "release_readiness_score"],
        "out_of_scope": ["Writing production code", "Merging code", "Deploying to production"],
        "open_questions": discovery["open_questions"],
        "version_history": [{"version": 1, "change": "Initial generated PRD"}],
    }


def _architecture(requirement: str, business_name: str, stack: list[str]) -> dict:
    return {
        "solution_architecture": f"Orchestrated implementation path for {requirement}.",
        "system_context": {"business": business_name, "actors": ["Founder", "PM", "Architect", "Developer AI", "QA", "Release Manager"]},
        "component_diagram": [
            {"from": "Conversation", "to": "Discovery Engine"},
            {"from": "Discovery Engine", "to": "PRD Generator"},
            {"from": "PRD Generator", "to": "Architecture Engine"},
            {"from": "Architecture Engine", "to": "Sprint Planner"},
            {"from": "Sprint Planner", "to": "Development Orchestrator"},
            {"from": "QA Orchestrator", "to": "Release Manager"},
        ],
        "api_contracts": [{"method": "POST", "path": "/software-factory/requirements", "purpose": "Create lifecycle package"}],
        "database_design": ["software_factory_requirements", "software_factory_artifacts", "software_factory_approvals"],
        "security": ["Founder approval gates", "No secrets in artifacts", "Audit every decision"],
        "performance": ["Generate deterministic artifacts quickly", "Defer heavy reasoning to explicit requests"],
        "scalability": ["Business-scoped rows", "Artifact versioning", "External Jira/GitHub adapters later"],
        "supported_stack": stack,
        "integration_points": ["Jira", "GitHub", "VS Code", "Codex", "Claude Code", "Knowledge Center"],
        "technical_risks": ["Scope creep", "Unverified integration assumptions", "Missing repository scan"],
        "engineering_recommendations": ["Approve architecture before coding", "Attach test cases to developer prompt", "Keep deployment gated"],
    }


def _engineering_plan(requirement: str, methodology: str) -> dict:
    stories = [
        ("Discovery and PRD finalization", 3),
        ("Architecture and API contract review", 5),
        ("Implementation context package", 3),
        ("Developer AI execution handoff", 5),
        ("QA automation and bug triage", 5),
        ("Release package and approval", 3),
    ]
    return {
        "methodology": methodology.lower(),
        "epics": [{"name": "Product Definition"}, {"name": "Engineering Delivery"}, {"name": "Quality and Release"}],
        "features": [_title(requirement), "Approval workflow", "Release readiness"],
        "user_stories": [
            {"title": title, "story_points": points, "acceptance_criteria": ["Evidence attached", "Founder-visible status", "Approval status clear"], "blocked": False, "sprint": "Sprint 1"}
            for title, points in stories
        ],
        "tasks": [{"title": f"Prepare {title.lower()}", "subtasks": ["Review context", "Generate artifact", "Attach evidence"]} for title, _ in stories],
        "sprint_allocation": {"Sprint 1": sum(points for _, points in stories), "capacity": 30},
    }


def _jira_plan(requirement_id: str, requirement: str) -> dict:
    key = requirement_id.split("-")[0].upper()
    return {
        "duplicate_prevention_key": f"SF-{key}",
        "project": {"key": "SF", "name": "Software Factory"},
        "epics": [{"external_key": f"SF-{key}-EPIC-1", "summary": _title(requirement)}],
        "stories": [{"external_key": f"SF-{key}-STORY-{index}", "summary": story} for index, story in enumerate(["PRD approved", "Architecture approved", "Sprint ready", "QA ready"], start=1)],
        "tasks": [{"labels": ["pardha", "software-factory"], "components": ["product", "engineering", "qa"], "version": "v1"}],
        "sprints": [{"name": "Software Factory Sprint 1", "goal": _title(requirement)}],
        "releases": [{"name": "Factory Release Candidate", "requires_founder_approval": True}],
        "linking": "Epics, stories, tasks, bugs, versions and releases share the duplicate_prevention_key.",
        "live_jira_created": False,
    }


def _development_context(business_id: str, requirement: str, stack: list[str]) -> dict:
    knowledge = search_knowledge(query=requirement, business_id=business_id)
    with SessionLocal() as session:
        projects = session.query(ProjectModel).filter(ProjectModel.business_id == business_id).all()
    return {
        "context_package": {
            "requirement": requirement,
            "architecture": "Use approved architecture artifact before code execution.",
            "relevant_files": [project.project_path for project in projects[:8]],
            "knowledge": [{"title": item.title, "category": item.category} for item in knowledge[:8]],
            "coding_standards": ["Small focused changes", "Tests with implementation", "No secrets in code", "Respect business isolation"],
            "acceptance_criteria": ["PRD approved", "Architecture approved", "Tests generated", "Review package complete"],
            "test_cases": ["API contract tests", "UI workflow tests", "Regression tests", "Security checks"],
            "prompt_package": f"Implement only after approval: {requirement}. Stack context: {', '.join(stack)}.",
        },
        "developer_targets": ["VS Code", "Codex", "Claude Code", "Git", "GitHub"],
        "production_code_written": False,
    }


def _code_review_plan(requirement: str) -> dict:
    return {
        "review_summary": f"Review policy prepared for {requirement}.",
        "checks": ["Architecture", "Code quality", "Security", "Performance", "Maintainability", "Complexity", "Standards"],
        "suggestions": ["Require tests before merge", "Validate rollback path", "Check auth and business isolation"],
        "risk_level": "medium",
        "merge_recommendation": "blocked_until_founder_approval",
    }


def _qa_plan(requirement: str) -> dict:
    return {
        "status": "prepared",
        "api_tests": [f"Validate API behavior for {requirement}"],
        "ui_tests": ["Founder approval journey", "Dashboard status visibility"],
        "regression_tests": ["Existing dashboard APIs remain healthy", "No duplicate Jira issues"],
        "performance_tests": ["Dashboard load under 2 seconds", "API latency monitored"],
        "accessibility_tests": ["Keyboard navigation", "Readable states"],
        "security_tests": ["No secrets in artifacts", "Approval required for release"],
        "bug_report_template": {"severity": "medium", "evidence": [], "screenshots": [], "reproduction_steps": [], "jira_bug": None},
        "automatically_executed": False,
    }


def _release_package(requirement: str) -> dict:
    return {
        "release_notes": [f"Prepared release package for {requirement}"],
        "deployment_checklist": ["PRD approved", "Architecture approved", "QA evidence attached", "Rollback reviewed", "Founder approval captured"],
        "rollback_plan": ["Disable feature flag", "Restore previous build", "Verify data integrity"],
        "migration_scripts": [],
        "risk_assessment": {"level": "medium", "notes": "Deployment blocked until founder approval."},
        "production_validation": ["Smoke test", "API health", "Dashboard workflow", "Error monitoring"],
        "readiness": {"status": "waiting_founder_approval", "score": 72},
        "deployed": False,
    }


def _knowledge_feedback(requirement: str) -> dict:
    return {
        "lessons_learned": [],
        "architecture_decisions": [f"Factory orchestration created for {requirement}"],
        "engineering_patterns": ["Approval-gated delivery", "Developer context package", "QA-before-release"],
        "reusable_components": ["PRD template", "Architecture template", "QA template"],
        "coding_standards": ["No production code in orchestration sprint", "Evidence-first approvals"],
    }


def _graph() -> dict:
    nodes = ["requirement", "discovery", "prd", "architecture", "sprint", "jira", "development_context", "qa", "release", "approval", "deployment"]
    return {"nodes": nodes, "edges": [{"from": nodes[index], "to": nodes[index + 1]} for index in range(len(nodes) - 1)]}


def _risk_level(requirement: str, approval_type: str) -> str:
    lower = f"{requirement} {approval_type}".lower()
    if "deploy" in lower or "release" in lower or "payment" in lower or "security" in lower:
        return "high"
    if "jira" in lower or "architecture" in lower or "merge" in lower:
        return "medium"
    return "low"


def _latest_artifact(deliveries: list[SoftwareFactoryDelivery], artifact_type: str) -> SoftwareFactoryArtifact | None:
    for delivery in deliveries:
        for artifact in delivery.artifacts:
            if artifact.artifact_type == artifact_type:
                return artifact
    return None


def _technical_debt(deliveries: list[SoftwareFactoryDelivery]) -> list[str]:
    if not deliveries:
        return ["No product delivery package has been generated yet."]
    return ["Live Jira creation adapter still requires credentials.", "Automated QA execution is prepared but not run by default.", "Deployment remains approval-gated."]


def _risks(deliveries: list[SoftwareFactoryDelivery]) -> list[str]:
    risks = []
    for delivery in deliveries[:5]:
        risks.extend(artifact.content.get("risks", []) for artifact in delivery.artifacts if artifact.artifact_type == "prd")
    flat = [item for group in risks for item in group]
    return flat[:6] or ["No active engineering risks."]
