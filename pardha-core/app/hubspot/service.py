from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func

from app.business.context import BusinessContextManager
from app.db import SessionLocal
from app.db.models import (
    HubSpotConnectorConfig as HubSpotConnectorConfigModel,
    HubSpotSyncRecord as HubSpotSyncRecordModel,
    SalesCompany as SalesCompanyModel,
    SalesContact as SalesContactModel,
    SalesDeal as SalesDealModel,
    SalesLead as SalesLeadModel,
)
from app.hubspot.client import HubSpotClient, HubSpotClientError
from app.hubspot.schemas import HubSpotConfigRequest, HubSpotConfigStatus, HubSpotLeadPayload, HubSpotSyncResult
from app.settings import get_settings


HUBSPOT_REQUIRED_ENV = ["HUBSPOT_ACCESS_TOKEN"]


def _business_id(business_id: str | None = None) -> str:
    return business_id or BusinessContextManager.get_active_business().business_id


def _env_status() -> tuple[bool, list[str]]:
    missing = [name for name in HUBSPOT_REQUIRED_ENV if not os.getenv(name)]
    return not missing, missing


def configure_hubspot(request: HubSpotConfigRequest) -> HubSpotConfigStatus:
    business_id = _business_id(request.business_id)
    env_valid, missing = _env_status()
    now = datetime.now(timezone.utc)
    status = "configured" if env_valid else "missing_environment"
    with SessionLocal() as session:
        row = (
            session.query(HubSpotConnectorConfigModel)
            .filter(HubSpotConnectorConfigModel.business_id == business_id)
            .one_or_none()
        )
        if row is None:
            row = HubSpotConnectorConfigModel(
                config_id=str(uuid4()),
                business_id=business_id,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
        row.portal_id = request.portal_id or os.getenv("HUBSPOT_PORTAL_ID") or row.portal_id
        row.status = status
        row.write_mode = request.write_mode
        row.scopes = request.scopes
        row.configuration = request.configuration
        row.secret_reference = request.secret_reference or row.secret_reference
        row.last_checked_at = now
        row.updated_at = now
        session.commit()
    return hubspot_status(business_id)


def hubspot_status(business_id: str | None = None) -> HubSpotConfigStatus:
    resolved_id = _business_id(business_id)
    env_valid, missing = _env_status()
    settings = get_settings()
    with SessionLocal() as session:
        row = (
            session.query(HubSpotConnectorConfigModel)
            .filter(HubSpotConnectorConfigModel.business_id == resolved_id)
            .one_or_none()
        )
    write_mode = row.write_mode if row else "disabled"
    live_writes = settings.connector_mode == "live" and env_valid and write_mode == "live"
    auth_status = "configured" if env_valid else "mock_contract" if settings.connector_mode == "mock" else "missing_environment"
    return HubSpotConfigStatus(
        business_id=resolved_id,
        status="ready" if live_writes else "safe_mode",
        portal_id=(row.portal_id if row else None) or os.getenv("HUBSPOT_PORTAL_ID") or None,
        write_mode=write_mode,
        scopes=row.scopes if row else ["crm.objects.contacts.read", "crm.objects.companies.read", "crm.objects.deals.read"],
        authentication_status=auth_status,
        environment_valid=env_valid,
        missing_environment=missing,
        last_checked_at=row.last_checked_at if row else None,
        message="HubSpot live writes enabled." if live_writes else "HubSpot writes are disabled; Pardha will create local sync drafts only.",
    )


def build_lead_payload(lead_id: str) -> HubSpotLeadPayload:
    lead, company, contact, deal = _lead_bundle(lead_id)
    email = (contact.email if contact else "") or ""
    duplicate_key = _duplicate_key(email=email, company_name=company.name)
    contact_payload = {
        "email": email,
        "firstname": _first_name(contact.name if contact else company.name),
        "lastname": _last_name(contact.name if contact else company.name),
        "jobtitle": contact.role if contact else "",
        "lifecyclestage": "opportunity",
        "lead_source": "Pardha DP360",
    }
    company_payload = {
        "name": company.name,
        "domain": _domain(company.website),
        "industry": company.industry,
        "country": company.country or "",
        "numberofemployees": _employee_count(company.company_size),
        "description": company.business_summary,
        "linkedin_company_page": company.linkedin_url or "",
    }
    deal_payload = {
        "dealname": lead.title,
        "amount": str(deal.amount if deal else 0),
        "dealstage": _hubspot_deal_stage(lead.pipeline_stage),
        "pipeline": "default",
        "dp360_lead_score": str(lead.ai_opportunity_score),
        "dp360_sales_priority": lead.sales_priority,
        "description": lead.next_action or "",
    }
    return HubSpotLeadPayload(lead_id=lead.lead_id, duplicate_key=duplicate_key, contact=contact_payload, company=company_payload, deal=deal_payload)


def sync_lead(lead_id: str, allow_write: bool = False, client: HubSpotClient | None = None) -> HubSpotSyncResult:
    lead, company, contact, deal = _lead_bundle(lead_id)
    payload = build_lead_payload(lead_id)
    now = datetime.now(timezone.utc)
    duplicate = _find_duplicate(lead.business_id, lead.lead_id, payload.duplicate_key)
    safe_mode = not _live_write_allowed(lead.business_id, allow_write)
    if duplicate:
        record = _write_record(
            lead=lead,
            contact=contact,
            company=company,
            deal=deal,
            payload=payload,
            action="duplicate_detected",
            sync_status="duplicate",
            duplicate_key=payload.duplicate_key,
            retryable=False,
            error=f"Duplicate HubSpot sync candidate already exists: {duplicate.sync_id}",
            now=now,
        )
        return _result(record, payload, duplicate=True, safe_mode=safe_mode, message="Duplicate lead detected by email or company name; HubSpot write skipped.")
    if safe_mode:
        record = _write_record(
            lead=lead,
            contact=contact,
            company=company,
            deal=deal,
            payload=payload,
            action="draft",
            sync_status="draft",
            duplicate_key=payload.duplicate_key,
            retryable=False,
            error=None,
            now=now,
        )
        return _result(record, payload, duplicate=False, safe_mode=True, message="HubSpot payload drafted locally. Live write requires PARDHA_CONNECTOR_MODE=live, config write_mode=live, credentials, and allow_write=true.")
    hubspot_client = client or HubSpotClient(os.getenv("HUBSPOT_ACCESS_TOKEN", ""))
    try:
        hubspot_company_id = hubspot_client.create_company(payload.company)
        hubspot_contact_id = hubspot_client.create_contact(payload.contact)
        hubspot_deal_id = hubspot_client.create_deal(payload.deal)
        record = _write_record(
            lead=lead,
            contact=contact,
            company=company,
            deal=deal,
            payload=payload,
            action="sync",
            sync_status="synced",
            duplicate_key=payload.duplicate_key,
            retryable=False,
            error=None,
            now=now,
            hubspot_contact_id=hubspot_contact_id,
            hubspot_company_id=hubspot_company_id,
            hubspot_deal_id=hubspot_deal_id,
        )
        return _result(record, payload, duplicate=False, safe_mode=False, message="HubSpot contact, company, and deal synced.")
    except HubSpotClientError as exc:
        record = _write_record(
            lead=lead,
            contact=contact,
            company=company,
            deal=deal,
            payload=payload,
            action="sync",
            sync_status="failed",
            duplicate_key=payload.duplicate_key,
            retryable=exc.retryable,
            error=str(exc),
            now=now,
        )
        return _result(record, payload, duplicate=False, safe_mode=False, message="HubSpot sync failed; retry status was recorded.")


def sync_history(business_id: str | None = None, limit: int = 50) -> list[HubSpotSyncResult]:
    resolved_id = _business_id(business_id)
    with SessionLocal() as session:
        rows = (
            session.query(HubSpotSyncRecordModel)
            .filter(HubSpotSyncRecordModel.business_id == resolved_id)
            .order_by(HubSpotSyncRecordModel.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [_result(row, _payload_from_record(row), duplicate=row.sync_status == "duplicate", safe_mode=row.sync_status == "draft", message=row.error or row.sync_status) for row in rows]


def _lead_bundle(lead_id: str) -> tuple[SalesLeadModel, SalesCompanyModel, SalesContactModel | None, SalesDealModel | None]:
    with SessionLocal() as session:
        lead = session.get(SalesLeadModel, lead_id)
        if lead is None:
            raise ValueError("Lead not found.")
        company = session.get(SalesCompanyModel, lead.company_id)
        if company is None:
            raise ValueError("Lead company not found.")
        contact = session.get(SalesContactModel, lead.contact_id) if lead.contact_id else None
        deal = session.query(SalesDealModel).filter(SalesDealModel.lead_id == lead.lead_id).first()
        session.expunge(lead)
        session.expunge(company)
        if contact is not None:
            session.expunge(contact)
        if deal is not None:
            session.expunge(deal)
        return lead, company, contact, deal


def _write_record(
    *,
    lead: SalesLeadModel,
    contact: SalesContactModel | None,
    company: SalesCompanyModel,
    deal: SalesDealModel | None,
    payload: HubSpotLeadPayload,
    action: str,
    sync_status: str,
    duplicate_key: str,
    retryable: bool,
    error: str | None,
    now: datetime,
    hubspot_contact_id: str | None = None,
    hubspot_company_id: str | None = None,
    hubspot_deal_id: str | None = None,
) -> HubSpotSyncRecordModel:
    with SessionLocal() as session:
        existing = (
            session.query(HubSpotSyncRecordModel)
            .filter(HubSpotSyncRecordModel.lead_id == lead.lead_id)
            .order_by(HubSpotSyncRecordModel.created_at.desc())
            .first()
        )
        row = existing or HubSpotSyncRecordModel(sync_id=str(uuid4()), business_id=lead.business_id, lead_id=lead.lead_id, created_at=now)
        row.local_contact_id = contact.contact_id if contact else None
        row.local_company_id = company.company_id
        row.local_deal_id = deal.deal_id if deal else None
        row.hubspot_contact_id = hubspot_contact_id or row.hubspot_contact_id
        row.hubspot_company_id = hubspot_company_id or row.hubspot_company_id
        row.hubspot_deal_id = hubspot_deal_id or row.hubspot_deal_id
        row.action = action
        row.sync_status = sync_status
        row.duplicate_key = duplicate_key
        row.retry_count = row.retry_count + 1 if sync_status == "failed" and existing else 0
        row.retryable = 1 if retryable else 0
        row.error = error
        row.contact_payload = payload.contact
        row.company_payload = payload.company
        row.deal_payload = payload.deal
        row.updated_at = now
        row = session.merge(row)
        session.commit()
        session.refresh(row)
        session.expunge(row)
        return row


def _find_duplicate(business_id: str, lead_id: str, duplicate_key: str) -> HubSpotSyncRecordModel | None:
    with SessionLocal() as session:
        return (
            session.query(HubSpotSyncRecordModel)
            .filter(HubSpotSyncRecordModel.business_id == business_id)
            .filter(HubSpotSyncRecordModel.lead_id != lead_id)
            .filter(func.lower(HubSpotSyncRecordModel.duplicate_key) == duplicate_key.lower())
            .first()
        )


def _live_write_allowed(business_id: str, allow_write: bool) -> bool:
    status = hubspot_status(business_id)
    return allow_write and status.environment_valid and status.write_mode == "live" and get_settings().connector_mode == "live"


def _result(record: HubSpotSyncRecordModel, payload: HubSpotLeadPayload, duplicate: bool, safe_mode: bool, message: str) -> HubSpotSyncResult:
    return HubSpotSyncResult(
        sync_id=record.sync_id,
        lead_id=record.lead_id,
        action=record.action,
        sync_status=record.sync_status,
        duplicate=duplicate,
        duplicate_key=record.duplicate_key,
        retry_count=record.retry_count,
        retryable=bool(record.retryable),
        error=record.error,
        hubspot_ids={"contact": record.hubspot_contact_id, "company": record.hubspot_company_id, "deal": record.hubspot_deal_id},
        payload=payload,
        safe_mode=safe_mode,
        message=message,
        updated_at=record.updated_at,
    )


def _payload_from_record(record: HubSpotSyncRecordModel) -> HubSpotLeadPayload:
    return HubSpotLeadPayload(lead_id=record.lead_id, duplicate_key=record.duplicate_key or "", contact=record.contact_payload or {}, company=record.company_payload or {}, deal=record.deal_payload or {})


def _duplicate_key(email: str, company_name: str) -> str:
    normalized_email = email.strip().lower()
    if normalized_email:
        return f"email:{normalized_email}"
    return f"company:{re.sub(r'[^a-z0-9]+', '-', company_name.lower()).strip('-')}"


def _domain(website: str | None) -> str:
    if not website:
        return ""
    return re.sub(r"^https?://", "", website).split("/")[0]


def _employee_count(size: str | None) -> str:
    if not size:
        return ""
    match = re.search(r"\d+", size.replace(",", ""))
    return match.group(0) if match else ""


def _first_name(name: str) -> str:
    return name.split()[0] if name else ""


def _last_name(name: str) -> str:
    parts = name.split()
    return " ".join(parts[1:]) if len(parts) > 1 else ""


def _hubspot_deal_stage(stage: str) -> str:
    mapping = {
        "prospecting": "appointmentscheduled",
        "demo_requested": "appointmentscheduled",
        "demo_scheduled": "qualifiedtobuy",
        "demo_completed": "presentationscheduled",
        "proposal_sent": "decisionmakerboughtin",
        "negotiation": "contractsent",
        "won": "closedwon",
        "lost": "closedlost",
    }
    return mapping.get(stage, "appointmentscheduled")
