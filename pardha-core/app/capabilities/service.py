from __future__ import annotations

import re
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from sqlalchemy import func

from app.business.service import resolve_business
from app.capabilities.defaults import DEFAULT_CAPABILITIES
from app.capabilities.executors import execute_adapter
from app.capabilities.schemas import (
    Capability,
    CapabilityCandidate,
    CapabilityExecutionRequest,
    CapabilityExecutionResult,
    CapabilityGraph,
    CapabilityHealth,
    CapabilityRegistration,
    CapabilitySearchRequest,
    CapabilitySearchResponse,
    RegistryValidationReport,
)
from app.db import SessionLocal
from app.db.models import Capability as CapabilityModel
from app.db.models import CapabilityExecution as CapabilityExecutionModel


HEALTH_WEIGHT = {"healthy": 20, "degraded": 8, "unknown": 2, "unavailable": -30}
STATUS_WEIGHT = {"registered": 10, "active": 10, "degraded": 2, "unregistered": -50}


def ensure_default_capabilities() -> list[Capability]:
    registered: list[Capability] = []
    for capability in DEFAULT_CAPABILITIES:
        registered.append(register_capability(capability, automatic=True))
    return registered


def register_capability(request: CapabilityRegistration, automatic: bool = False) -> Capability:
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = session.get(CapabilityModel, request.capability_id)
        if row is None:
            row = CapabilityModel(
                capability_id=request.capability_id,
                registered_at=now,
                execution_count=0,
            )
            session.add(row)
        row.name = request.name.strip()
        row.version = request.version.strip()
        row.description = request.description.strip()
        row.supported_intents = request.supported_intents
        row.business_domains = request.business_domains
        row.required_inputs = request.required_inputs
        row.outputs = request.outputs
        row.dependencies = request.dependencies
        row.permissions = request.permissions
        row.health = request.health
        row.supports_hitl = 1 if request.supports_hitl else 0
        row.supports_streaming = 1 if request.supports_streaming else 0
        row.supports_learning = 1 if request.supports_learning else 0
        row.priority = request.priority
        row.estimated_runtime_ms = request.estimated_runtime_ms
        row.registration_method = "automatic" if automatic else request.registration_method
        row.current_status = request.current_status
        row.planner_interface = request.planner_interface
        row.execution_adapter = request.execution_adapter
        row.updated_at = now
        session.commit()
        session.refresh(row)
        return _capability(row)


def unregister_capability(capability_id: str) -> dict[str, bool | str]:
    with SessionLocal() as session:
        row = session.get(CapabilityModel, capability_id)
        if row is None:
            return {"unregistered": False, "capability_id": capability_id}
        row.current_status = "unregistered"
        row.health = "unavailable"
        row.updated_at = datetime.now(timezone.utc)
        session.commit()
        return {"unregistered": True, "capability_id": capability_id}


def list_capabilities(include_unregistered: bool = False) -> list[Capability]:
    ensure_default_capabilities()
    with SessionLocal() as session:
        query = session.query(CapabilityModel)
        if not include_unregistered:
            query = query.filter(CapabilityModel.current_status != "unregistered")
        rows = query.order_by(CapabilityModel.priority.desc(), CapabilityModel.name.asc()).all()
        return [_capability(row) for row in rows]


def get_capability(capability_id: str) -> Capability | None:
    ensure_default_capabilities()
    with SessionLocal() as session:
        row = session.get(CapabilityModel, capability_id)
        return _capability(row) if row is not None else None


def search_capabilities(request: CapabilitySearchRequest) -> CapabilitySearchResponse:
    ensure_default_capabilities()
    with SessionLocal() as session:
        rows = (
            session.query(CapabilityModel)
            .filter(CapabilityModel.current_status != "unregistered")
            .all()
        )
        candidates = [_candidate(row, request) for row in rows]
    filtered = [candidate for candidate in candidates if candidate.confidence > 0 or not request.intent and not request.query]
    filtered.sort(key=lambda item: (item.score, item.confidence, item.capability.priority), reverse=True)
    return CapabilitySearchResponse(
        intent=request.intent,
        query=request.query,
        candidates=filtered[: request.max_results],
    )


def capability_health() -> CapabilityHealth:
    capabilities = list_capabilities()
    counts = {"healthy": 0, "degraded": 0, "unavailable": 0, "unknown": 0}
    for capability in capabilities:
        counts[capability.health if capability.health in counts else "unknown"] += 1
    return CapabilityHealth(
        total=len(capabilities),
        healthy=counts["healthy"],
        degraded=counts["degraded"],
        unavailable=counts["unavailable"],
        unknown=counts["unknown"],
        capabilities=capabilities,
    )


def execute_capability(request: CapabilityExecutionRequest) -> CapabilityExecutionResult:
    ensure_default_capabilities()
    business = None
    if request.business_id or request.business_name:
        business = resolve_business(business_id=request.business_id, business_name=request.business_name)

    if request.capability_id:
        capability = get_capability(request.capability_id)
        if capability is None:
            raise ValueError(f"Unknown capability_id: {request.capability_id}")
        confidence = 100
    else:
        search = search_capabilities(
            CapabilitySearchRequest(
                intent=request.intent,
                query=request.payload.get("query", request.intent),
                business_id=business.business_id if business else None,
                required_inputs=request.required_inputs,
                max_results=1,
            )
        )
        if not search.candidates:
            raise ValueError("No registered capability can satisfy the requested intent.")
        selected = search.candidates[0]
        capability = selected.capability
        confidence = selected.confidence

    started = perf_counter()
    execution_id = str(uuid4())
    output: dict = {}
    status = "succeeded"
    error = None
    try:
        output = execute_adapter(capability.execution_adapter, business_id=business.business_id if business else None, payload=request.payload)
    except Exception as exc:  # pragma: no cover - stored as API evidence
        status = "failed"
        error = str(exc)
    runtime_ms = max(1, int((perf_counter() - started) * 1000))
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = CapabilityExecutionModel(
            execution_id=execution_id,
            capability_id=capability.capability_id,
            business_id=business.business_id if business else None,
            intent=request.intent,
            input_payload=request.payload,
            output_payload=output if status == "succeeded" else None,
            status=status,
            confidence=confidence,
            runtime_ms=runtime_ms,
            error=error,
            created_at=now,
        )
        session.add(row)
        capability_row = session.get(CapabilityModel, capability.capability_id)
        if capability_row is not None:
            capability_row.execution_count += 1
            capability_row.last_executed_at = now
            capability_row.updated_at = now
        session.commit()
    return CapabilityExecutionResult(
        execution_id=execution_id,
        capability_id=capability.capability_id,
        status=status,
        confidence=confidence,
        runtime_ms=runtime_ms,
        output=output,
        error=error,
    )


def capability_graph() -> CapabilityGraph:
    capabilities = list_capabilities()
    nodes = [
        {
            "id": capability.capability_id,
            "label": capability.name,
            "health": capability.health,
            "priority": capability.priority,
            "version": capability.version,
        }
        for capability in capabilities
    ]
    edges = []
    capability_ids = {capability.capability_id for capability in capabilities}
    for capability in capabilities:
        for dependency in capability.dependencies:
            target = dependency if dependency in capability_ids else f"dependency:{dependency}"
            if target not in capability_ids:
                nodes.append({"id": target, "label": dependency, "type": "dependency"})
            edges.append({"source": capability.capability_id, "target": target, "type": "depends_on"})
    return CapabilityGraph(nodes=nodes, edges=edges)


def validation_report() -> RegistryValidationReport:
    capabilities = list_capabilities()
    missing = []
    for capability in capabilities:
        for field in ("capability_id", "name", "version", "description"):
            if not getattr(capability, field):
                missing.append(f"{capability.capability_id}.{field}")
    ids = [capability.capability_id for capability in capabilities]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    unhealthy = [capability.capability_id for capability in capabilities if capability.health == "unavailable"]
    expected = {capability.capability_id for capability in DEFAULT_CAPABILITIES}
    actual = set(ids)
    return RegistryValidationReport(
        total_capabilities=len(capabilities),
        registered_existing_capabilities=len(expected & actual),
        missing_required_fields=missing,
        unhealthy_capabilities=unhealthy,
        duplicate_ids=duplicates,
        ready=not missing and not duplicates and len(expected - actual) == 0,
    )


def _candidate(row: CapabilityModel, request: CapabilitySearchRequest) -> CapabilityCandidate:
    capability = _capability(row)
    intent_tokens = _tokens(request.intent)
    query_tokens = _tokens(request.query)
    haystack = _tokens(
        " ".join(
            [
                capability.capability_id,
                capability.name,
                capability.description,
                " ".join(capability.supported_intents),
                " ".join(capability.business_domains),
                " ".join(capability.outputs),
            ]
        )
    )
    supported_tokens = set(_tokens(" ".join(capability.supported_intents)))
    domain_match = bool(request.business_domain and request.business_domain.lower() in [item.lower() for item in capability.business_domains])
    exact_intent = request.intent.lower() in [item.lower() for item in capability.supported_intents]
    token_hits = len((set(intent_tokens) | set(query_tokens)) & set(haystack))
    supported_hits = len((set(intent_tokens) | set(query_tokens)) & supported_tokens)
    missing_inputs = [item for item in capability.required_inputs if item not in request.required_inputs and item not in {"business_id"}]

    confidence = min(100, (55 if exact_intent else 0) + supported_hits * 12 + token_hits * 4 + (12 if domain_match else 0))
    score = (
        confidence
        + capability.priority
        + HEALTH_WEIGHT.get(capability.health, 0)
        + STATUS_WEIGHT.get(capability.current_status, 0)
        - min(20, capability.estimated_runtime_ms // 100)
        - len(missing_inputs) * 5
    )
    reasons = []
    if exact_intent:
        reasons.append("exact_intent_match")
    if supported_hits:
        reasons.append(f"supported_intent_terms:{supported_hits}")
    if token_hits:
        reasons.append(f"semantic_terms:{token_hits}")
    if domain_match:
        reasons.append("business_domain_match")
    if capability.health != "healthy":
        reasons.append(f"health:{capability.health}")
    if missing_inputs:
        reasons.append(f"missing_optional_inputs:{','.join(missing_inputs)}")
    return CapabilityCandidate(capability=capability, confidence=confidence, score=score, reasons=reasons)


def _capability(row: CapabilityModel) -> Capability:
    return Capability(
        capability_id=row.capability_id,
        name=row.name,
        version=row.version,
        description=row.description,
        supported_intents=row.supported_intents or [],
        business_domains=row.business_domains or [],
        required_inputs=row.required_inputs or [],
        outputs=row.outputs or [],
        dependencies=row.dependencies or [],
        permissions=row.permissions or [],
        health=row.health,
        supports_hitl=bool(row.supports_hitl),
        supports_streaming=bool(row.supports_streaming),
        supports_learning=bool(row.supports_learning),
        priority=row.priority,
        estimated_runtime_ms=row.estimated_runtime_ms,
        registration_method=row.registration_method,
        current_status=row.current_status,
        planner_interface=row.planner_interface or {},
        execution_adapter=row.execution_adapter,
        execution_count=row.execution_count,
        last_executed_at=row.last_executed_at,
        registered_at=row.registered_at,
        updated_at=row.updated_at,
    )


def _tokens(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", value.lower()) if token]
