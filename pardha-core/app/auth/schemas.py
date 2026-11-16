from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)
    remember_me: bool = False


class UserProfile(BaseModel):
    user_id: str
    tenant_id: Optional[str] = None
    email: str
    full_name: str
    role: str
    status: str


class LoginResponse(BaseModel):
    authenticated: bool
    token: str
    jwt_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_at: datetime
    user: UserProfile


class SessionStatus(BaseModel):
    authenticated: bool
    user: Optional[UserProfile] = None
    expires_at: Optional[datetime] = None


class SecurityStatus(BaseModel):
    password_hashing: str
    environment_admin_configured: bool
    plaintext_credentials_stored: bool
    session_storage: str
    production_mode: str
    jwt_authentication: str = "hs256_ready"
    refresh_tokens: str = "database_hashed"
    mfa_ready: bool = True
    rate_limiting: str = "enabled"
