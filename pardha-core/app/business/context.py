from __future__ import annotations

from threading import Lock

from app.business.schemas import Business, BusinessContext


class BusinessContextManager:
    _active_business_id: str | None = None
    _lock = Lock()

    @classmethod
    def set_active_business(cls, business_id: str | None = None, business_name: str | None = None) -> Business:
        from app.business.service import resolve_business

        business = resolve_business(business_id=business_id, business_name=business_name)
        with cls._lock:
            cls._active_business_id = business.business_id
        return business

    @classmethod
    def get_active_business(cls) -> Business:
        from app.business.service import get_business, list_businesses

        with cls._lock:
            active_id = cls._active_business_id
        if active_id:
            business = get_business(active_id)
            if business is not None:
                return business
        businesses = list_businesses()
        default = next((item for item in businesses if item.business_name == "DP360"), businesses[0])
        with cls._lock:
            cls._active_business_id = default.business_id
        return default

    @classmethod
    def get_business_context(cls) -> BusinessContext:
        from app.business.summary import build_business_context

        return build_business_context(cls.get_active_business().business_id)
