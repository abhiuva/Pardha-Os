from __future__ import annotations

from fastapi import APIRouter, Query

from app.commercial.schemas import ConnectorStatus, ConnectorTestResult, DemoLoadResult, FounderDashboard, GuidedJourney, SystemHealth
from app.commercial.service import connector_statuses, founder_dashboard, guided_journey, load_dp360_demo, system_health, test_connector


router = APIRouter(prefix="/commercial", tags=["commercial-readiness"])


@router.get("/connectors/status", response_model=list[ConnectorStatus])
def get_connector_statuses():
    return connector_statuses()


@router.post("/connectors/{provider}/test", response_model=ConnectorTestResult)
def test_connector_route(provider: str):
    return test_connector(provider)


@router.get("/founder-dashboard", response_model=FounderDashboard)
def get_founder_dashboard(business_id: str | None = Query(default=None)):
    return founder_dashboard(business_id=business_id)


@router.get("/system/health", response_model=SystemHealth)
def get_system_health():
    return system_health()


@router.get("/demo/journey", response_model=GuidedJourney)
def get_guided_journey(business_id: str | None = Query(default=None)):
    return guided_journey(business_id=business_id)


@router.post("/demo/dp360", response_model=DemoLoadResult)
def load_dp360_demo_route():
    return load_dp360_demo()
