from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HubSpotClientError(RuntimeError):
    def __init__(self, message: str, retryable: bool = False):
        super().__init__(message)
        self.retryable = retryable


@dataclass
class HubSpotClient:
    access_token: str
    base_url: str = "https://api.hubapi.com"

    def create_contact(self, payload: Dict[str, Any]) -> str:
        return self._create_object("contacts", payload)

    def create_company(self, payload: Dict[str, Any]) -> str:
        return self._create_object("companies", payload)

    def create_deal(self, payload: Dict[str, Any]) -> str:
        return self._create_object("deals", payload)

    def _create_object(self, object_type: str, payload: Dict[str, Any]) -> str:
        body = json.dumps({"properties": payload}).encode("utf-8")
        request = Request(
            f"{self.base_url}/crm/v3/objects/{object_type}",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            retryable = exc.code in {408, 429, 500, 502, 503, 504}
            raise HubSpotClientError(f"HubSpot {object_type} create failed with HTTP {exc.code}.", retryable=retryable) from exc
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise HubSpotClientError(f"HubSpot {object_type} create failed: {exc}", retryable=True) from exc
        object_id = data.get("id")
        if not object_id:
            raise HubSpotClientError(f"HubSpot {object_type} response did not include an id.", retryable=False)
        return str(object_id)
