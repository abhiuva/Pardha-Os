from __future__ import annotations

import hashlib
import hmac
import base64
import json
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.auth.schemas import LoginResponse, SecurityStatus, SessionStatus, UserProfile
from app.db import SessionLocal
from app.db.models import AuthRefreshToken as AuthRefreshTokenModel
from app.db.models import AuthSession as AuthSessionModel
from app.db.models import AuthUser as AuthUserModel
from app.settings import get_settings


ITERATIONS = 210_000
SESSION_HOURS = 12
REMEMBER_DAYS = 30


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, iterations, salt_hex, derived_hex = stored_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)).hex()
        return hmac.compare_digest(candidate, derived_hex)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_jwt(user: AuthUserModel, expires_at: datetime) -> str:
    secret = os.getenv("PARDHA_JWT_SECRET", "pardha-dev-jwt-secret-change-me")
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user.user_id,
        "tenant_id": user.tenant_id,
        "email": user.email,
        "role": user.role,
        "exp": int(expires_at.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp()),
    }
    signing_input = f"{_b64(header)}.{_b64(payload)}"
    signature = hmac.new(secret.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode('ascii')}"


def ensure_admin_user() -> UserProfile:
    email = os.getenv("PARDHA_ADMIN_EMAIL", "founder@pardha.local").strip().lower()
    password = os.getenv("PARDHA_ADMIN_PASSWORD")
    configured_hash = os.getenv("PARDHA_ADMIN_PASSWORD_HASH")
    full_name = os.getenv("PARDHA_ADMIN_NAME", "Abhishek")
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        user = session.query(AuthUserModel).filter(AuthUserModel.email == email).one_or_none()
        if user is None:
            password_hash = configured_hash or hash_password(password or secrets.token_urlsafe(32))
            user = AuthUserModel(
                user_id=str(uuid4()),
                email=email,
                password_hash=password_hash,
                full_name=full_name,
                role="founder",
                status="active",
                created_at=now,
                updated_at=now,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
        return _profile(user)


def login(email: str, password: str, remember_me: bool = False) -> LoginResponse:
    ensure_admin_user()
    normalized = email.strip().lower()
    if "@" not in normalized:
        raise ValueError("Invalid email address.")
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        user = session.query(AuthUserModel).filter(AuthUserModel.email == normalized, AuthUserModel.status == "active").one_or_none()
        if user is None or not verify_password(password, user.password_hash):
            raise ValueError("Invalid email or password.")
        raw_token = secrets.token_urlsafe(32)
        raw_refresh = secrets.token_urlsafe(48)
        expires = now + (timedelta(days=REMEMBER_DAYS) if remember_me else timedelta(hours=SESSION_HOURS))
        session.add(
            AuthSessionModel(
                session_id=str(uuid4()),
                user_id=user.user_id,
                token_hash=token_hash(raw_token),
                remember_me=1 if remember_me else 0,
                expires_at=expires,
                created_at=now,
                last_seen_at=now,
            )
        )
        session.add(
            AuthRefreshTokenModel(
                refresh_token_id=str(uuid4()),
                user_id=user.user_id,
                tenant_id=user.tenant_id,
                token_hash=token_hash(raw_refresh),
                expires_at=now + timedelta(days=30),
                revoked_at=None,
                created_at=now,
            )
        )
        session.commit()
        return LoginResponse(authenticated=True, token=raw_token, jwt_token=create_jwt(user, expires), refresh_token=raw_refresh, expires_at=expires, user=_profile(user))


def session_status(token: str | None) -> SessionStatus:
    if not token:
        return SessionStatus(authenticated=False)
    now = datetime.now(timezone.utc)
    with SessionLocal() as session:
        row = session.query(AuthSessionModel).filter(AuthSessionModel.token_hash == token_hash(token)).one_or_none()
        if row is None or _as_aware(row.expires_at) <= now:
            return SessionStatus(authenticated=False)
        user = session.get(AuthUserModel, row.user_id)
        if user is None or user.status != "active":
            return SessionStatus(authenticated=False)
        row.last_seen_at = now
        session.commit()
        return SessionStatus(authenticated=True, user=_profile(user), expires_at=row.expires_at)


def logout(token: str | None) -> dict[str, bool]:
    if token:
        with SessionLocal() as session:
            session.query(AuthSessionModel).filter(AuthSessionModel.token_hash == token_hash(token)).delete()
            session.query(AuthRefreshTokenModel).filter(AuthRefreshTokenModel.token_hash == token_hash(token)).delete()
            session.commit()
    return {"logged_out": True}


def security_status() -> SecurityStatus:
    settings = get_settings()
    return SecurityStatus(
        password_hashing="pbkdf2_sha256",
        environment_admin_configured=bool(os.getenv("PARDHA_ADMIN_EMAIL") and os.getenv("PARDHA_ADMIN_PASSWORD")),
        plaintext_credentials_stored=False,
        session_storage="database_opaque_token_hash",
        production_mode=settings.mode.value,
    )


def _profile(user: AuthUserModel) -> UserProfile:
    return UserProfile(user_id=user.user_id, tenant_id=user.tenant_id, email=user.email, full_name=user.full_name, role=user.role, status=user.status)


def _as_aware(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _b64(payload: dict) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
