from fastapi import APIRouter, Header, HTTPException, status

from app.auth.schemas import LoginRequest, LoginResponse, SecurityStatus, SessionStatus
from app.auth.service import ensure_admin_user, login, logout, security_status, session_status

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login_route(request: LoginRequest):
    try:
        return login(request.email, request.password, request.remember_me)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/session", response_model=SessionStatus)
def session_route(authorization: str | None = Header(default=None)):
    token = _bearer_token(authorization)
    return session_status(token)


@router.post("/logout")
def logout_route(authorization: str | None = Header(default=None)):
    return logout(_bearer_token(authorization))


@router.get("/profile", response_model=SessionStatus)
def profile_route(authorization: str | None = Header(default=None)):
    status_payload = session_status(_bearer_token(authorization))
    if not status_payload.authenticated:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized.")
    return status_payload


@router.get("/security", response_model=SecurityStatus)
def security_route():
    ensure_admin_user()
    return security_status()


def _bearer_token(value: str | None) -> str | None:
    if not value:
        return None
    prefix = "Bearer "
    return value[len(prefix) :].strip() if value.startswith(prefix) else value.strip()
