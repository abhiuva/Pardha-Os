from fastapi import APIRouter, HTTPException

from app.sales.schemas import (
    CalendarAvailabilityResponse,
    DemoBookingRecord,
    DemoBookingRequest,
    DemoBookingStatusRequest,
    DemoScheduleRequest,
    DemoScheduleResult,
    DemoScheduleResponse,
    LeadQualificationRequest,
    LeadQualificationResult,
    PostDemoDraftRecord,
    PostDemoDraftRequest,
    ProspectRequest,
    ProspectGenerationResult,
    SalesDashboard,
    SalesLeadDetail,
    SalesOutreachPackage,
    SalesPipelineResponse,
    SalesSummary,
    StageUpdateRequest,
    StageUpdateResult,
)
from app.sales.service import (
    build_prospect_research,
    calendar_availability,
    create_demo_booking,
    create_post_demo_draft,
    get_dashboard,
    get_demos,
    get_outreach_package,
    get_pipeline,
    get_summary,
    list_demo_bookings,
    list_leads,
    list_post_demo_drafts,
    qualify_lead,
    schedule_demo,
    update_demo_booking_status,
    update_stage,
)

router = APIRouter(prefix="/sales", tags=["sales"])


@router.post("/prospect", response_model=ProspectGenerationResult)
def create_sales_prospect(request: ProspectRequest):
    return build_prospect_research(
        query=request.query,
        target_count=request.target_count,
        industries=request.industries,
    )


@router.get("/leads", response_model=list[SalesLeadDetail])
def get_sales_leads():
    return list_leads()


@router.get("/leads/{lead_id}/outreach", response_model=SalesOutreachPackage)
def get_sales_lead_outreach(lead_id: str):
    try:
        return get_outreach_package(lead_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/leads/{lead_id}/qualify", response_model=LeadQualificationResult)
def qualify_sales_lead(lead_id: str, request: LeadQualificationRequest):
    try:
        return qualify_lead(lead_id=lead_id, request=request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/leads/{lead_id}/schedule-demo", response_model=DemoScheduleResult)
def schedule_sales_demo(lead_id: str, request: DemoScheduleRequest):
    try:
        return schedule_demo(
            lead_id=lead_id,
            scheduled_at=request.scheduled_at,
            meeting_url=request.meeting_url,
            owner=request.owner,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/leads/{lead_id}/demo-booking", response_model=DemoBookingRecord)
def create_sales_demo_booking(lead_id: str, request: DemoBookingRequest):
    try:
        return create_demo_booking(lead_id=lead_id, request=request)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/calendar/availability", response_model=CalendarAvailabilityResponse)
def get_calendar_availability(days: int = 5):
    return calendar_availability(days=days)


@router.get("/demo-bookings", response_model=list[DemoBookingRecord])
def get_demo_bookings(business_id: str | None = None):
    return list_demo_bookings(business_id=business_id)


@router.post("/demo-bookings/{booking_id}/status", response_model=DemoBookingRecord)
def update_demo_booking(booking_id: str, request: DemoBookingStatusRequest):
    try:
        return update_demo_booking_status(booking_id=booking_id, request=request)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/demo-bookings/{booking_id}/post-demo-draft", response_model=PostDemoDraftRecord)
def create_post_demo_follow_up(booking_id: str, request: PostDemoDraftRequest):
    try:
        return create_post_demo_draft(booking_id=booking_id, request=request)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/post-demo-drafts", response_model=list[PostDemoDraftRecord])
def get_post_demo_drafts(lead_id: str | None = None, booking_id: str | None = None):
    return list_post_demo_drafts(lead_id=lead_id, booking_id=booking_id)


@router.post("/leads/{lead_id}/stage", response_model=StageUpdateResult)
def update_sales_stage(lead_id: str, request: StageUpdateRequest):
    try:
        return update_stage(lead_id=lead_id, status=request.status)
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 400
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/pipeline", response_model=SalesPipelineResponse)
def get_sales_pipeline():
    return get_pipeline()


@router.get("/demos", response_model=DemoScheduleResponse)
def get_sales_demos():
    return get_demos()


@router.get("/summary", response_model=SalesSummary)
def get_sales_summary():
    return get_summary()


@router.get("/dashboard", response_model=SalesDashboard)
def get_sales_dashboard():
    return get_dashboard()
