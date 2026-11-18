from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from app.security.write_guard import guard_external_write
from app.settings import get_settings

_READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


class JiraConfigurationError(RuntimeError):
    pass


class JiraClient:
    def __init__(
        self,
        *,
        jira_url: str,
        email: str,
        api_token: str,
        project_key: str,
        timeout: float = 20.0,
    ):
        self.jira_url = jira_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.project_key = project_key
        self.timeout = timeout

    @classmethod
    def from_settings(cls) -> "JiraClient":
        settings = get_settings()
        if not settings.jira_enabled:
            raise JiraConfigurationError("Jira integration is disabled.")
        missing = [
            name
            for name, value in {
                "JIRA_URL": settings.jira_url,
                "JIRA_EMAIL": settings.jira_email,
                "JIRA_API_TOKEN": settings.jira_api_token,
                "JIRA_PROJECT_KEY": settings.jira_project_key,
            }.items()
            if not value
        ]
        if missing:
            raise JiraConfigurationError(f"Missing Jira configuration: {', '.join(missing)}.")
        return cls(
            jira_url=settings.jira_url,
            email=settings.jira_email,
            api_token=settings.jira_api_token,
            project_key=settings.jira_project_key,
        )

    def create_epic(self, summary: str, description: str = "") -> Dict[str, Any]:
        return self._create_issue("Epic", summary, description)

    def create_story(
        self,
        summary: str,
        description: str = "",
        *,
        parent_key: Optional[str] = None,
        technical: bool = False,
    ) -> Dict[str, Any]:
        labels = ["pardha", "technical"] if technical else ["pardha"]
        return self._create_issue("Story", summary, description, parent_key=parent_key, labels=labels)

    def update_issue(self, issue_key: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        self._request("PUT", f"/rest/api/3/issue/{issue_key}", json={"fields": fields})
        return self.get_issue(issue_key)

    def transition_issue(self, issue_key: str, status: str) -> Dict[str, Any]:
        # A transition is a write. Enforce the write boundary before the preliminary lookup, so a
        # blocked transition sends nothing at all (not even the GET that lists transitions).
        guard_external_write("jira", f"POST /rest/api/3/issue/{issue_key}/transitions")
        transitions =self._request("GET", f"/rest/api/3/issue/{issue_key}/transitions").get("transitions", [])
        transition = next(
            (
                item
                for item in transitions
                if item.get("name", "").lower() == status.lower()
                or item.get("to", {}).get("name", "").lower() == status.lower()
            ),
            None,
        )
        if transition is None:
            raise ValueError(f"No Jira transition found for status '{status}'.")
        self._request(
            "POST",
            f"/rest/api/3/issue/{issue_key}/transitions",
            json={"transition": {"id": transition["id"]}},
        )
        return self.get_issue(issue_key)

    def get_issue(self, issue_key: str) -> Dict[str, Any]:
        return self._request("GET", f"/rest/api/3/issue/{issue_key}")

    def search_issues(self, jql: str, max_results: int = 50) -> Dict[str, Any]:
        return self._request(
            "GET",
            "/rest/api/3/search",
            params={"jql": jql, "maxResults": max_results},
        )

    def _create_issue(
        self,
        issue_type: str,
        summary: str,
        description: str,
        *,
        parent_key: Optional[str] = None,
        labels: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        fields: Dict[str, Any] = {
            "project": {"key": self.project_key},
            "summary": summary,
            "issuetype": {"name": issue_type},
            "labels": labels or ["pardha"],
        }
        if description:
            fields["description"] = _adf_description(description)
        if parent_key:
            fields["parent"] = {"key": parent_key}
        return self._request("POST", "/rest/api/3/issue", json={"fields": fields})

    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        if method.upper() not in _READ_ONLY_METHODS:
            guard_external_write("jira", f"{method.upper()} {path}")
        with httpx.Client(
            base_url=self.jira_url,
            auth=(self.email, self.api_token),
            timeout=self.timeout,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        ) as client:
            response = client.request(method, path, **kwargs)
        response.raise_for_status()
        if not response.content:
            return {}
        return response.json()


def _adf_description(description: str) -> Dict[str, Any]:
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": description}],
            }
        ],
    }
