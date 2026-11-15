from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from uuid import uuid4


@dataclass(frozen=True)
class ConnectorMessage:
    provider_message_id: str
    provider_thread_id: str
    sender: str
    recipients: list[str]
    cc: list[str]
    bcc: list[str]
    subject: str
    body: str
    labels: list[str]
    is_read: bool
    sent_at: datetime | None = None
    received_at: datetime | None = None


class MailConnector(Protocol):
    provider: str

    def read_emails(self, account_email: str, limit: int = 25) -> list[ConnectorMessage]:
        ...

    def send_email(
        self,
        account_email: str,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> ConnectorMessage:
        ...

    def draft_email(
        self,
        account_email: str,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> ConnectorMessage:
        ...

    def search_emails(self, account_email: str, query: str, limit: int = 25) -> list[ConnectorMessage]:
        ...

    def retrieve_threads(self, account_email: str, limit: int = 25) -> list[ConnectorMessage]:
        ...


class _EnvConnector:
    provider = ""
    token_env = ""

    def _network_enabled(self) -> bool:
        return os.getenv("PARDHA_COMMUNICATIONS_ENABLE_NETWORK", "false").lower() in {"1", "true", "yes"}

    def _configured(self) -> bool:
        return bool(os.getenv(self.token_env))

    def _mock_message(
        self,
        account_email: str,
        recipients: list[str],
        subject: str,
        body: str,
        *,
        status: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> ConnectorMessage:
        now = datetime.now(timezone.utc)
        message_id = f"{self.provider}-{status}-{uuid4()}"
        return ConnectorMessage(
            provider_message_id=message_id,
            provider_thread_id=f"{self.provider}-thread-{uuid4()}",
            sender=account_email,
            recipients=recipients,
            cc=cc or [],
            bcc=bcc or [],
            subject=subject,
            body=body,
            labels=[status],
            is_read=True,
            sent_at=now if status == "sent" else None,
            received_at=None,
        )

    def _unsupported_network(self) -> None:
        raise RuntimeError(
            f"{self.provider} network API calls are disabled. Set PARDHA_COMMUNICATIONS_ENABLE_NETWORK=true "
            f"and provide {self.token_env} to use the live provider."
        )

    def read_emails(self, account_email: str, limit: int = 25) -> list[ConnectorMessage]:
        if self._network_enabled() and self._configured():
            self._unsupported_network()
        return []

    def send_email(
        self,
        account_email: str,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> ConnectorMessage:
        if self._network_enabled() and self._configured():
            self._unsupported_network()
        return self._mock_message(account_email, recipients, subject, body, status="sent", cc=cc, bcc=bcc)

    def draft_email(
        self,
        account_email: str,
        recipients: list[str],
        subject: str,
        body: str,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
    ) -> ConnectorMessage:
        if self._network_enabled() and self._configured():
            self._unsupported_network()
        return self._mock_message(account_email, recipients, subject, body, status="draft", cc=cc, bcc=bcc)

    def search_emails(self, account_email: str, query: str, limit: int = 25) -> list[ConnectorMessage]:
        return self.read_emails(account_email, limit=limit)

    def retrieve_threads(self, account_email: str, limit: int = 25) -> list[ConnectorMessage]:
        return self.read_emails(account_email, limit=limit)


class GmailConnector(_EnvConnector):
    provider = "gmail"
    token_env = "PARDHA_GMAIL_ACCESS_TOKEN"


class OutlookConnector(_EnvConnector):
    provider = "outlook"
    token_env = "PARDHA_OUTLOOK_ACCESS_TOKEN"


def get_connector(provider: str) -> MailConnector:
    normalized = provider.strip().lower()
    if normalized == "gmail":
        return GmailConnector()
    if normalized in {"outlook", "microsoft365", "microsoft_365"}:
        return OutlookConnector()
    raise ValueError(f"Unsupported communications provider: {provider}")
