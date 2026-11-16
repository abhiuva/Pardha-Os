from __future__ import annotations

import os
from typing import Any, Dict


SECRET_KEYS = {"access_token", "refresh_token", "client_secret", "api_key", "password", "token"}


def resolve_credentials(provider: str, credentials: Dict[str, Any] | None = None) -> Dict[str, Any]:
    merged = dict(credentials or {})
    if provider == "meta":
        merged.setdefault("access_token", os.getenv("META_ACCESS_TOKEN", ""))
        merged.setdefault("business_account_id", os.getenv("META_BUSINESS_ACCOUNT_ID", ""))
        merged.setdefault("ad_account_id", os.getenv("META_AD_ACCOUNT_ID", ""))
        merged.setdefault("page_id", os.getenv("META_PAGE_ID", ""))
        merged.setdefault("instagram_account_id", os.getenv("META_INSTAGRAM_ACCOUNT_ID", ""))
    if provider == "hubspot":
        merged.setdefault("access_token", os.getenv("HUBSPOT_ACCESS_TOKEN", ""))
        merged.setdefault("portal_id", os.getenv("HUBSPOT_PORTAL_ID", ""))
    return merged


def authentication_status(provider: str, credentials: Dict[str, Any] | None = None) -> str:
    resolved = resolve_credentials(provider, credentials)
    if provider == "meta":
        return "configured" if resolved.get("access_token") and resolved.get("ad_account_id") else "missing_credentials"
    if provider == "hubspot":
        return "configured" if resolved.get("access_token") else "missing_credentials"
    return "configured" if any(resolved.values()) else "missing_credentials"


def redact_credentials(credentials: Dict[str, Any] | None = None) -> Dict[str, Any]:
    redacted: Dict[str, Any] = {}
    for key, value in (credentials or {}).items():
        if key.lower() in SECRET_KEYS:
            redacted[key] = "***configured***" if value else ""
        else:
            redacted[key] = value
    return redacted
