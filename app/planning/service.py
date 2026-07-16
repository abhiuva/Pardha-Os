from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.capabilities.schemas import CapabilityExecutionRequest, CapabilitySearchRequest
from app.capabilities.service import execute_capability, search_capabilities
from app.db import SessionLocal
from app.db.models import ExecutionPlan as ExecutionPlanModel
from app.db.models import ExecutionPlanNode as ExecutionPlanNodeModel
from app.db.models import GoalKPI as GoalKPIModel
from app.db.models import PlanApproval as PlanApprovalModel
from app.db.models import PlanExecution as PlanExecutionModel
from app.db.models import PlanningGoal as PlanningGoalModel
from app.db.models import PlanningTimelineEvent as PlanningTimelineEventModel
from app.planning.schemas import (
    ApprovalDecision,
    DailyExecutivePlan,
    ExecutionPlan,
    ExecutionPlanNode,
    GoalKPI,
    PlanApproval,
    PlanExecution,
    PlanRequest,
    PlanningGoal,
    PlanningResult,
    PlanningTimelineEvent,
)


HIGH_RISK_TERMS = ("send email", "launch campaign", "deploy", "merge code", "delete", "production")
MEDIUM_RISK_TERMS = ("acquire", "get ", "need ", "create", "develop", "feature", "jira", "document", "task", "goal", "sprint", "customer", "pilot")


def create_plan(request: PlanRequest) -> PlanningResult:
    now = datetime.now(timezone.utc)
    plan_type = _plan_type(request.request)
    risk_level = _risk_level(request.request)
    approval_required = risk_level in {"medium", "high"} and not request.approve
    goal_id = str(uuid4())
    plan_id = str(uuid4())
    capabilities = _negotiate_capabilities(request.request, plan_type, request.business_id)
    capability_ids = [item["capability_id"] for item in capabilities]
    steps = _steps_for_plan(request.request, plan_type, capabilities, risk_level)
    graph = _graph(steps)
    success_metrics = _success_metrics(request.request, plan_type)

    with SessionLocal() as session:
        goal = PlanningGoalModel(
            goal_id=goal_id,
            business_id=request.business_id,
            title=_title(request.request),
            description=request.request.strip(),
            priority=request.priority,
            owner=request.owner,
            department=_department(plan_type),
            target_date=now + timedelta(days=14),
            success_metrics=success_metrics,
            current_status="active",
            risk_level=risk_level,
            progress=0,
            dependencies=[],
            created_by=request.owner,
            created_at=now,
            updated_at=now,
        )
        plan = ExecutionPlanModel(
            plan_id=plan_id,
            goal_id=goal_id,
            business_id=request.business_id,
            title=f"Execution plan: {_title(request.request)}",
            request=request.request.strip(),
            plan_type=plan_type,
            status="waiting_approval" if approval_required else "preview",
            risk_level=risk_level,
            approval_required=1 if approval_required else 0,
            progress=0,
            estimated_completion=now + timedelta(days=14),
            summary=f"Executable {plan_type} plan with {len(steps)} graph nodes and {len(capability_ids)} negotiated capabilities.",
            capability_ids=capability_ids,
            graph=graph,
            created_by=request.owner,
            created_at=now,
            updated_at=now,
        )
        session.add(goal)
        session.add(plan)
        node_rows = []
        for step in steps:
            row = ExecutionPlanNodeModel(
                node_id=step["node_id"],
                plan_id=plan_id,
                goal_id=goal_id,
                business_id=request.business_id,
                node_type=step["node_type"],
                title=step["title"],
                description=step["description"],
                capability_id=step.get("capability_id"),
                status="waiting_approval" if step["approval_required"] else "queued",
                risk_level=step["risk_level"],
                approval_required=1 if step["approval_required"] else 0,
                dependencies=step["dependencies"],
                parallel_group=step.get("parallel_group"),
                critical_path=1 if step["critical_path"] else 0,
                estimated_runtime_ms=step["estimated_runtime_ms"],
                output=None,
                created_at=now,
                updated_at=now,
            )
            node_rows.append(row)
            session.add(row)
        approvals = []
        if approval_required:
            approval = PlanApprovalModel(
                approval_id=str(uuid4()),
                plan_id=plan_id,
                node_id=None,
                business_id=request.business_id,
                approval_type="plan_execution",
                risk_level=risk_level,
                title=f"Approve plan: {_title(request.request)}",
                detail="Founder approval is required before executing this plan.",
                status="pending",
                requested_by="Planner",
                decided_by=None,
                decision_comment=None,
                created_at=now,
                decided_at=None,
            )
            approvals.append(approval)
            session.add(approval)
        kpis = []
        for metric in success_metrics:
            kpi = GoalKPIModel(
                kpi_id=str(uuid4()),
                goal_id=goal_id,
                business_id=request.business_id,
                name=metric,
                target_value=_target_value(metric, request.request),
                current_value=0,
                unit="count",
                status="tracking",
                updated_at=now,
            )
            kpis.append(kpi)
            session.add(kpi)
        _timeline(session, goal_id, plan_id, request.business_id, "goal_created", "Goal Created", goal.title, {"risk_level": risk_level})
        _timeline(session, goal_id, plan_id, request.business_id, "plan_generated", "Execution Plan Generated", plan.summary, {"capability_ids": capability_ids})
        if approval_required:
            _timeline(session, goal_id, plan_id, request.business_id, "approval_required", "Approval Required", "Plan is waiting for founder approval.", {"risk_level": risk_level})
        session.commit()
    return get_plan(plan_id)


def list_goals(business_id: str | None = None) -> list[PlanningGoal]:
    with SessionLocal() as session:
        query = session.query(PlanningGoalModel)
        if business_id:
            query = query.filter(PlanningGoalModel.business_id == business_id)
        return [_goal(row) for row in query.order_by(PlanningGoalModel.updated_at.desc()).all()]


def list_plans(business_id: str | None = None) -> list[ExecutionPlan]:
    with SessionLocal() as session:
        query = session.query(ExecutionPlanModel)
        if business_id:
            query = query.filter(ExecutionPlanModel.business_id == business_id)
        plans = []
        for row in query.order_by(ExecutionPlanModel.updated_at.desc()).all():
            plans.append(_plan(row, _nodes(session, row.plan_id)))
        return plans


def get_plan(plan_id: str) -> PlanningResult:
    with SessionLocal() as session:
        plan = session.get(ExecutionPlanModel, plan_id)
        if plan is None:
            raise ValueError("Plan not found.")
        goal = session.get(PlanningGoalModel, plan.goal_id)
        approvals = session.query(PlanApprovalModel).filter(PlanApprovalModel.plan_id == plan_id).order_by(PlanApprovalModel.created_at.asc()).all()
        kpis = session.query(GoalKPIModel).filter(GoalKPIModel.goal_id == plan.goal_id).order_by(GoalKPIModel.name.asc()).all()
        timeline = session.query(PlanningTimelineEventModel).filter(PlanningTimelineEventModel.plan_id == plan_id).order_by(PlanningTimelineEventModel.created_at.asc()).all()
        return PlanningResult(
            goal=_goal(goal),
            plan=_plan(plan, _nodes(session, plan_id)),
            approvals=[_approval(row) for row in approvals],
            kpis=[_kpi(row) for row in kpis],
            timeline=[_timeline_schema(row) for row in timeline],
        )


def list_approvals(business_id: str | None = None, status: str | None = "pending") -> list[PlanApproval]:
    with SessionLocal() as session:
        query = session.query(PlanApprovalModel)
        if business_id:
            query = query.filter(PlanApprovalModel.business_id == business_id)
        if status:
            query = query.filter(PlanApprovalModel.status == status)
        return [_approval(row) for row in query.order_by(PlanApprovalModel.created_at.desc()).all()]


def approve_plan(plan_id: str, decision: ApprovalDecision) -> PlanningResult:
    return _decide_plan(plan_id, decision, "approved")


def reject_plan(plan_id: str, decision: ApprovalDecision) -> PlanningResult:
    return _decide_plan(plan_id, decision, "rejected")


def execute_plan(plan_id: str) -> PlanExecution:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        plan = session.get(ExecutionPlanModel, plan_id)
        if plan is None:
            raise ValueError("Plan not found.")
        pending = session.query(PlanApprovalModel).filter(PlanApprovalModel.plan_id == plan_id, PlanApprovalModel.status == "pending").count()
        if pending:
            execution = _create_execution(session, plan, "waiting_approval", now, [{"event": "waiting_approval", "detail": "Approval required before execution."}])
            session.commit()
            return _execution(execution)

        nodes = session.query(ExecutionPlanNodeModel).filter(ExecutionPlanNodeModel.plan_id == plan_id).order_by(ExecutionPlanNodeModel.created_at.asc()).all()
        logs = []
        completed = 0
        execution = _create_execution(session, plan, "running", now, logs)
        for node in nodes:
            if node.approval_required:
                node.status = "waiting_approval"
                logs.append({"event": "node_waiting_approval", "node_id": node.node_id, "title": node.title})
                continue
            if node.capability_id:
                result = execute_capability(CapabilityExecutionRequest(intent=node.node_type, capability_id=node.capability_id, business_id=plan.business_id, payload={"plan_id": plan_id, "goal_id": plan.goal_id, "node_title": node.title}))
                node.output = {"execution_id": result.execution_id, "status": result.status, "output": result.output}
                node.status = "completed" if result.status == "succeeded" else "failed"
                logs.append({"event": "capability_executed", "node_id": node.node_id, "capability_id": node.capability_id, "status": result.status})
            else:
                node.status = "completed"
                node.output = {"status": "tracked", "detail": "No capability adapter required for this graph node."}
                logs.append({"event": "node_completed", "node_id": node.node_id})
            node.updated_at = datetime.now(timezone.utc)
            if node.status == "completed":
                completed += 1
        total = max(1, len(nodes))
        execution.progress = int(completed / total * 100)
        execution.logs = logs
        execution.status = "completed" if completed == total else "waiting_approval"
        execution.completed_at = datetime.now(timezone.utc) if execution.status == "completed" else None
        execution.updated_at = datetime.now(timezone.utc)
        plan.progress = execution.progress
        plan.status = execution.status
        plan.updated_at = execution.updated_at
        goal = session.get(PlanningGoalModel, plan.goal_id)
        goal.progress = execution.progress
        goal.current_status = "completed" if execution.status == "completed" else "active"
        goal.updated_at = execution.updated_at
        _timeline(session, plan.goal_id, plan_id, plan.business_id, "execution_completed", "Execution Updated", execution.status, {"progress": execution.progress})
        session.commit()
        session.refresh(execution)
        return _execution(execution)


def daily_executive_plan(business_id: str) -> DailyExecutivePlan:
    goals = list_goals(business_id)
    active = [goal for goal in goals if goal.current_status != "completed"]
    titles = [goal.title for goal in active[:5]]
    blocked = [goal.title for goal in active if goal.risk_level == "high" or goal.progress < 25][:5]
    return DailyExecutivePlan(
        business_id=business_id,
        ceo_priorities=[f"Review progress for {title}" for title in titles[:3]] or ["Create the first active business goal."],
        marketing_priorities=[title for title in titles if "campaign" in title.lower() or "customer" in title.lower() or "pilot" in title.lower()],
        sales_priorities=[title for title in titles if "customer" in title.lower() or "sales" in title.lower() or "pilot" in title.lower()],
        engineering_priorities=[title for title in titles if "feature" in title.lower() or "backend" in title.lower() or "engineering" in title.lower()],
        operations_priorities=["Clear pending approvals", "Review execution timeline"],
        qa_priorities=["Verify completed plan outputs", "Review blocked items"],
        blocked_items=blocked,
        recommended_actions=["Approve pending medium/high-risk plans", "Execute approved plans", "Update KPIs at end of day"],
    )


def plan_timeline(goal_id: str) -> list[PlanningTimelineEvent]:
    with SessionLocal() as session:
        rows = session.query(PlanningTimelineEventModel).filter(PlanningTimelineEventModel.goal_id == goal_id).order_by(PlanningTimelineEventModel.created_at.asc()).all()
        return [_timeline_schema(row) for row in rows]


def goal_kpis(goal_id: str) -> list[GoalKPI]:
    with SessionLocal() as session:
        rows = session.query(GoalKPIModel).filter(GoalKPIModel.goal_id == goal_id).order_by(GoalKPIModel.name.asc()).all()
        return [_kpi(row) for row in rows]


def _negotiate_capabilities(request: str, plan_type: str, business_id: str) -> list[dict]:
    intents = _intents_for_plan(request, plan_type)
    selected = []
    seen = set()
    for intent in intents:
        result = search_capabilities(CapabilitySearchRequest(intent=intent, query=request, business_id=business_id, max_results=1))
        if result.candidates:
            candidate = result.candidates[0]
            if candidate.capability.capability_id not in seen:
                seen.add(candidate.capability.capability_id)
                selected.append({"capability_id": candidate.capability.capability_id, "intent": intent, "confidence": candidate.confidence, "score": candidate.score, "runtime": candidate.capability.estimated_runtime_ms})
    return selected


def _steps_for_plan(request: str, plan_type: str, capabilities: list[dict], risk_level: str) -> list[dict]:
    steps = [
        ("objective", "Clarify business objective", "Confirm owner, success metrics, scope, and business context.", None, "low"),
    ]
    for item in capabilities:
        steps.append(("capability", f"Execute {item['capability_id']}", f"Run capability for {item['intent']}.", item, "low"))
    if plan_type in {"sales", "growth"}:
        steps.extend([
            ("milestone", "Marketing strategy ready", "Prepare positioning, campaign message, and content angle.", None, "medium"),
            ("milestone", "Sales plan ready", "Prepare prospecting, CRM stages, and demo follow-up plan.", None, "medium"),
            ("verification", "KPI review", "Verify pilots, leads, meetings, demos, and pipeline progress.", None, "low"),
        ])
    elif plan_type in {"engineering", "product"}:
        steps.extend([
            ("milestone", "PRD and architecture ready", "Confirm requirements, architecture, sprint, QA, and release gates.", None, "medium"),
            ("verification", "QA and release verification", "Verify development, tests, bugs, and release readiness.", None, "low"),
        ])
    else:
        steps.append(("verification", "Executive verification", "Verify outputs, blocked items, and next actions.", None, "low"))
    built = []
    previous = None
    for index, (node_type, title, description, capability, node_risk) in enumerate(steps):
        node_id = str(uuid4())
        approval = _node_approval_required(title, node_risk, risk_level)
        built.append({
            "node_id": node_id,
            "node_type": node_type,
            "title": title,
            "description": description,
            "capability_id": capability["capability_id"] if capability else None,
            "risk_level": "high" if any(term in title.lower() for term in HIGH_RISK_TERMS) else node_risk,
            "approval_required": approval,
            "dependencies": [previous] if previous else [],
            "parallel_group": "capabilities" if node_type == "capability" else None,
            "critical_path": index == 0 or node_type == "verification",
            "estimated_runtime_ms": capability["runtime"] if capability else 100,
        })
        previous = node_id if node_type != "capability" else previous
    return built


def _graph(steps: list[dict]) -> dict:
    return {
        "nodes": [{"id": step["node_id"], "label": step["title"], "type": step["node_type"], "status": "queued"} for step in steps],
        "edges": [{"source": dep, "target": step["node_id"], "type": "depends_on"} for step in steps for dep in step["dependencies"]],
        "critical_path": [step["node_id"] for step in steps if step["critical_path"]],
        "parallel_groups": sorted({step["parallel_group"] for step in steps if step.get("parallel_group")}),
    }


def _decide_plan(plan_id: str, decision: ApprovalDecision, status: str) -> PlanningResult:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        plan = session.get(ExecutionPlanModel, plan_id)
        if plan is None:
            raise ValueError("Plan not found.")
        approvals = session.query(PlanApprovalModel).filter(PlanApprovalModel.plan_id == plan_id, PlanApprovalModel.status == "pending").all()
        for approval in approvals:
            approval.status = status
            approval.decided_by = decision.decided_by
            approval.decision_comment = decision.comment
            approval.decided_at = now
        plan.status = "approved" if status == "approved" else "rejected"
        plan.approval_required = 0 if status == "approved" else plan.approval_required
        plan.updated_at = now
        _timeline(session, plan.goal_id, plan_id, plan.business_id, f"approval_{status}", f"Plan {status.title()}", decision.comment, {})
        session.commit()
    return get_plan(plan_id)


def _create_execution(session, plan: ExecutionPlanModel, status: str, now: datetime, logs: list[dict]) -> PlanExecutionModel:
    execution = PlanExecutionModel(
        execution_id=str(uuid4()),
        plan_id=plan.plan_id,
        goal_id=plan.goal_id,
        business_id=plan.business_id,
        current_step="approval" if status == "waiting_approval" else "execution",
        current_capability=None,
        progress=0,
        estimated_time_ms=sum(node.get("estimated_runtime_ms", 0) for node in (plan.graph or {}).get("nodes", [])),
        logs=logs,
        retry_count=0,
        status=status,
        started_at=now if status == "running" else None,
        completed_at=None,
        created_at=now,
        updated_at=now,
    )
    session.add(execution)
    return execution


def _plan_type(request: str) -> str:
    text = request.lower()
    if any(term in text for term in ("pilot", "customer", "sales", "prospect", "crm")):
        return "sales"
    if any(term in text for term in ("campaign", "marketing", "lead")):
        return "marketing"
    if any(term in text for term in ("feature", "backend", "sprint", "prd", "engineering")):
        return "engineering"
    if any(term in text for term in ("roadmap", "product")):
        return "product"
    return "growth"


def _intents_for_plan(request: str, plan_type: str) -> list[str]:
    if plan_type == "sales":
        return ["business_review", "marketing_summary", "sales_summary", "task_review"]
    if plan_type == "marketing":
        return ["marketing_summary", "sales_summary", "business_review"]
    if plan_type == "engineering":
        return ["product_review", "architecture_review", "task_review", "project_review"]
    if plan_type == "product":
        return ["product_review", "sprint_planning", "architecture_review"]
    return ["business_review", "executive_summary", "task_review"]


def _success_metrics(request: str, plan_type: str) -> list[str]:
    text = request.lower()
    if "5" in text or "five" in text or "pilot" in text:
        return ["Pilot Customers", "Meetings Booked", "Demos Scheduled", "Pipeline Value"]
    if plan_type == "engineering":
        return ["Sprint Completion", "Bugs Closed", "Engineering Velocity", "Release Readiness"]
    if plan_type == "marketing":
        return ["Leads Generated", "Campaign CTR", "Landing Page Conversions", "Pipeline Contribution"]
    return ["Revenue", "Tasks Completed", "Blocked Items Cleared", "Knowledge Growth"]


def _risk_level(request: str) -> str:
    text = request.lower()
    if any(term in text for term in HIGH_RISK_TERMS):
        return "high"
    if any(term in text for term in MEDIUM_RISK_TERMS):
        return "medium"
    return "low"


def _node_approval_required(title: str, node_risk: str, plan_risk: str) -> bool:
    text = title.lower()
    return plan_risk == "high" or node_risk == "high" or any(term in text for term in ("email", "campaign", "jira", "deploy", "delete", "merge"))


def _department(plan_type: str) -> str:
    return {"sales": "Sales", "marketing": "Marketing", "engineering": "Engineering", "product": "Product"}.get(plan_type, "Executive")


def _title(request: str) -> str:
    return " ".join(request.strip().split())[:90] or "Business Goal"


def _target_value(metric: str, request: str) -> int:
    if "Pilot Customers" in metric:
        return 5
    if "Meetings" in metric or "Demos" in metric:
        return 3
    if "Completion" in metric or "Readiness" in metric:
        return 100
    return 10


def _nodes(session, plan_id: str) -> list[ExecutionPlanNode]:
    rows = session.query(ExecutionPlanNodeModel).filter(ExecutionPlanNodeModel.plan_id == plan_id).order_by(ExecutionPlanNodeModel.created_at.asc()).all()
    return [_node(row) for row in rows]


def _timeline(session, goal_id: str, plan_id: str | None, business_id: str, event_type: str, title: str, detail: str, payload: dict) -> None:
    session.add(PlanningTimelineEventModel(timeline_event_id=str(uuid4()), goal_id=goal_id, plan_id=plan_id, business_id=business_id, event_type=event_type, title=title, detail=detail, payload=payload, created_at=datetime.now(timezone.utc)))


def _goal(row: PlanningGoalModel) -> PlanningGoal:
    return PlanningGoal(goal_id=row.goal_id, business_id=row.business_id, title=row.title, description=row.description, priority=row.priority, owner=row.owner, department=row.department, target_date=row.target_date, success_metrics=row.success_metrics or [], current_status=row.current_status, risk_level=row.risk_level, progress=row.progress, dependencies=row.dependencies or [], created_by=row.created_by, created_at=row.created_at, updated_at=row.updated_at)


def _plan(row: ExecutionPlanModel, nodes: list[ExecutionPlanNode]) -> ExecutionPlan:
    return ExecutionPlan(plan_id=row.plan_id, goal_id=row.goal_id, business_id=row.business_id, title=row.title, request=row.request, plan_type=row.plan_type, status=row.status, risk_level=row.risk_level, approval_required=bool(row.approval_required), progress=row.progress, estimated_completion=row.estimated_completion, summary=row.summary, capability_ids=row.capability_ids or [], graph=row.graph or {}, created_by=row.created_by, created_at=row.created_at, updated_at=row.updated_at, nodes=nodes)


def _node(row: ExecutionPlanNodeModel) -> ExecutionPlanNode:
    return ExecutionPlanNode(node_id=row.node_id, plan_id=row.plan_id, goal_id=row.goal_id, business_id=row.business_id, node_type=row.node_type, title=row.title, description=row.description, capability_id=row.capability_id, status=row.status, risk_level=row.risk_level, approval_required=bool(row.approval_required), dependencies=row.dependencies or [], parallel_group=row.parallel_group, critical_path=bool(row.critical_path), estimated_runtime_ms=row.estimated_runtime_ms, output=row.output, created_at=row.created_at, updated_at=row.updated_at)


def _approval(row: PlanApprovalModel) -> PlanApproval:
    return PlanApproval(approval_id=row.approval_id, plan_id=row.plan_id, node_id=row.node_id, business_id=row.business_id, approval_type=row.approval_type, risk_level=row.risk_level, title=row.title, detail=row.detail, status=row.status, requested_by=row.requested_by, decided_by=row.decided_by, decision_comment=row.decision_comment, created_at=row.created_at, decided_at=row.decided_at)


def _execution(row: PlanExecutionModel) -> PlanExecution:
    return PlanExecution(execution_id=row.execution_id, plan_id=row.plan_id, goal_id=row.goal_id, business_id=row.business_id, current_step=row.current_step, current_capability=row.current_capability, progress=row.progress, estimated_time_ms=row.estimated_time_ms, logs=row.logs or [], retry_count=row.retry_count, status=row.status, started_at=row.started_at, completed_at=row.completed_at, created_at=row.created_at, updated_at=row.updated_at)


def _kpi(row: GoalKPIModel) -> GoalKPI:
    return GoalKPI(kpi_id=row.kpi_id, goal_id=row.goal_id, business_id=row.business_id, name=row.name, target_value=row.target_value, current_value=row.current_value, unit=row.unit, status=row.status, updated_at=row.updated_at)


def _timeline_schema(row: PlanningTimelineEventModel) -> PlanningTimelineEvent:
    return PlanningTimelineEvent(timeline_event_id=row.timeline_event_id, goal_id=row.goal_id, plan_id=row.plan_id, business_id=row.business_id, event_type=row.event_type, title=row.title, detail=row.detail, payload=row.payload or {}, created_at=row.created_at)
