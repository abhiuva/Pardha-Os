from fastapi import APIRouter, HTTPException, status

from app.business.context import BusinessContextManager
from app.business.schemas import Business, BusinessContext, BusinessCreate, ContextSwitchRequest
from app.business.service import create_business, get_business, list_businesses


router = APIRouter(tags=["business-context"])


@router.post("/businesses", response_model=Business, status_code=status.HTTP_201_CREATED)
def create_business_route(business: BusinessCreate):
    return create_business(business)


@router.get("/businesses", response_model=list[Business])
def list_businesses_route():
    return list_businesses()


@router.get("/businesses/{business_id}", response_model=Business)
def get_business_route(business_id: str):
    business = get_business(business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found.")
    return business


@router.post("/context/switch", response_model=BusinessContext)
def switch_context_route(request: ContextSwitchRequest):
    try:
        BusinessContextManager.set_active_business(
            business_id=request.business_id,
            business_name=request.business_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return BusinessContextManager.get_business_context()


@router.get("/context/current", response_model=BusinessContext)
def get_current_context_route():
    return BusinessContextManager.get_business_context()
