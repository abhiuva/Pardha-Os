from fastapi import APIRouter, HTTPException, status

from app.copilot.schemas import (
    BusinessHealthDashboard,
    BusinessIntelligenceReport,
    CommercialReadinessReport,
    ConsultantRequest,
    ConsultantResponse,
    CustomerSuccessWorkspace,
    DemoLibrary,
    DemoWorkspaceRequest,
    DemoWorkspaceResult,
    ExecutiveBriefBundle,
    FounderCopilotRequest,
    FounderCopilotResult,
    OnboardingRequest,
    OnboardingResult,
    PresentationMode,
)
from app.copilot.service import (
    business_intelligence,
    commercial_readiness_report,
    consultant_response,
    customer_workspace,
    demo_library,
    executive_briefs,
    health_dashboard,
    load_demo_workspace,
    onboard_customer,
    presentation_mode,
    run_founder_copilot,
)

router = APIRouter(prefix="/copilot", tags=["founder-copilot"])


@router.post("/founder", response_model=FounderCopilotResult, status_code=status.HTTP_201_CREATED)
def founder_copilot(request: FounderCopilotRequest):
    return run_founder_copilot(request)


@router.get("/business-intelligence", response_model=BusinessIntelligenceReport)
def get_business_intelligence(business_id: str | None = None, business_name: str | None = None):
    return business_intelligence(business_id=business_id, business_name=business_name)


@router.get("/customer-workspace", response_model=CustomerSuccessWorkspace)
def get_customer_workspace(business_id: str | None = None, business_name: str | None = None):
    return customer_workspace(business_id=business_id, business_name=business_name)


@router.get("/executive-briefs", response_model=ExecutiveBriefBundle)
def get_executive_briefs(business_id: str | None = None, business_name: str | None = None):
    return executive_briefs(business_id=business_id, business_name=business_name)


@router.get("/health-dashboard", response_model=BusinessHealthDashboard)
def get_business_health_dashboard(business_id: str | None = None, business_name: str | None = None):
    return health_dashboard(business_id=business_id, business_name=business_name)


@router.post("/consultant", response_model=ConsultantResponse)
def ask_business_consultant(request: ConsultantRequest):
    return consultant_response(question=request.question, business_id=request.business_id, business_name=request.business_name)


@router.post("/onboarding", response_model=OnboardingResult)
def run_customer_onboarding(request: OnboardingRequest):
    return onboard_customer(request)


@router.get("/demo-library", response_model=DemoLibrary)
def get_demo_library():
    return demo_library()


@router.post("/demo-library/load", response_model=DemoWorkspaceResult)
def load_demo(request: DemoWorkspaceRequest):
    try:
        return load_demo_workspace(request.template)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/presentation", response_model=PresentationMode)
def get_presentation_mode(business_id: str | None = None, business_name: str | None = None):
    return presentation_mode(business_id=business_id, business_name=business_name)


@router.get("/commercial-readiness", response_model=CommercialReadinessReport)
def get_commercial_readiness_report():
    return commercial_readiness_report()
