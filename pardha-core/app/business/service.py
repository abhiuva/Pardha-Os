from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Iterable, Optional
from uuid import uuid4

from sqlalchemy import func

from app.business.schemas import Business, BusinessCreate
from app.db import SessionLocal
from app.db.models import Business as BusinessModel
from app.db.models import Tenant as TenantModel


DEFAULT_BUSINESSES: tuple[dict[str, str], ...] = (
    {
        "business_name": "UVA",
        "business_type": "education",
        "description": "UVA business operating context.",
    },
    {
        "business_name": "DP360",
        "business_type": "data_platform",
        "description": "DP360 business operating context.",
    },
    {
        "business_name": "EatOnTime",
        "business_type": "foodtech",
        "description": "EatOnTime school meal operations context.",
    },
    {
        "business_name": "Trevia EV",
        "business_type": "ev",
        "description": "Trevia EV electric mobility operating context.",
    },
)

FOLDER_TO_BUSINESS = {
    "uva": "UVA",
    "dp360": "DP360",
    "eatontime": "EatOnTime",
    "trevia": "Trevia EV",
}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _row_to_business(row: BusinessModel) -> Business:
    return Business.model_validate(row)


def ensure_default_businesses() -> list[Business]:
    with SessionLocal() as session:
        tenant_id = _default_tenant_id(session)
        rows: list[BusinessModel] = []
        for item in DEFAULT_BUSINESSES:
            existing = (
                session.query(BusinessModel)
                .filter(func.lower(BusinessModel.business_name) == item["business_name"].lower())
                .one_or_none()
            )
            if existing is None:
                existing = BusinessModel(
                    business_id=str(uuid4()),
                    tenant_id=tenant_id,
                    business_name=item["business_name"],
                    business_type=item["business_type"],
                    description=item["description"],
                    status="active",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(existing)
            rows.append(existing)
        session.commit()
        return [_row_to_business(row) for row in rows]


def create_business(data: BusinessCreate | dict) -> Business:
    validated = BusinessCreate.model_validate(data)
    with SessionLocal() as session:
        existing = (
            session.query(BusinessModel)
            .filter(func.lower(BusinessModel.business_name) == validated.business_name.strip().lower())
            .one_or_none()
        )
        if existing is not None:
            return _row_to_business(existing)
        row = BusinessModel(
            business_id=str(uuid4()),
            tenant_id=validated.tenant_id or _default_tenant_id(session),
            business_name=validated.business_name.strip(),
            business_type=validated.business_type.strip(),
            description=validated.description.strip(),
            status=validated.status.strip(),
            created_at=datetime.now(timezone.utc),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return _row_to_business(row)


def list_businesses() -> list[Business]:
    ensure_default_businesses()
    with SessionLocal() as session:
        rows = (
            session.query(BusinessModel)
            .order_by(BusinessModel.business_name.asc(), BusinessModel.business_id.asc())
            .all()
        )
        return [_row_to_business(row) for row in rows]


def get_business(business_id: str) -> Optional[Business]:
    ensure_default_businesses()
    with SessionLocal() as session:
        row = session.get(BusinessModel, business_id)
        return _row_to_business(row) if row is not None else None


def get_business_by_name(business_name: str) -> Optional[Business]:
    ensure_default_businesses()
    with SessionLocal() as session:
        row = (
            session.query(BusinessModel)
            .filter(func.lower(BusinessModel.business_name) == business_name.strip().lower())
            .one_or_none()
        )
        return _row_to_business(row) if row is not None else None


def resolve_business(
    *,
    business_id: Optional[str] = None,
    business_name: Optional[str] = None,
    text: Optional[str] = None,
) -> Business:
    ensure_default_businesses()
    if business_id:
        business = get_business(business_id)
        if business is not None:
            return business
        raise ValueError(f"Unknown business_id: {business_id}")

    if business_name and business_name.strip():
        mapped_name = FOLDER_TO_BUSINESS.get(business_name.strip().lower(), business_name.strip())
        business = get_business_by_name(mapped_name)
        if business is not None:
            return business
        return create_business(
            {
                "business_name": mapped_name,
                "business_type": "company",
                "description": f"{mapped_name} business operating context.",
            }
        )

    normalized_text = _normalize(text or "")
    for business in list_businesses():
        if _normalize(business.business_name) in normalized_text:
            return business

    from app.business.context import BusinessContextManager

    return BusinessContextManager.get_active_business()


def resolve_business_from_folder(folder_name: str) -> Business:
    return resolve_business(business_name=FOLDER_TO_BUSINESS.get(folder_name.lower(), folder_name))


def find_business_in_text(text_values: Iterable[str]) -> Business:
    return resolve_business(text=" ".join(value for value in text_values if value))


def get_active_business() -> Business:
    from app.business.context import BusinessContextManager

    return BusinessContextManager.get_active_business()


def _default_tenant_id(session) -> str | None:
    tenant = session.query(TenantModel).filter(TenantModel.slug == "pardha-internal").one_or_none()
    return tenant.tenant_id if tenant is not None else None
