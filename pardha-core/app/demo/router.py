from __future__ import annotations

from fastapi import APIRouter, status

from app.demo.schemas import DemoSeedResult, FounderCopilotRequest, FounderCopilotResponse
from app.demo.service import ensure_demo_data, run_founder_copilot


router = APIRouter(tags=["demo-readiness"])


@router.post("/demo/seed", response_model=DemoSeedResult, status_code=status.HTTP_201_CREATED)
def seed_demo_data_route():
    return ensure_demo_data()


@router.post("/copilot/founder", response_model=FounderCopilotResponse, status_code=status.HTTP_201_CREATED)
def founder_copilot_route(request: FounderCopilotRequest):
    return run_founder_copilot(
        prompt=request.prompt,
        business_name=request.business_name,
        priority=request.priority,
    )
