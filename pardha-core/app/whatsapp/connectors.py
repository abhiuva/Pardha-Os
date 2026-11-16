from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class WhatsAppProviderMessage:
    provider_message_id: str
    sender_phone: str
    recipient_phone: str
    body: str
    status: str
    message_type: str = "text"
    template_name: str | None = None
    sent_at: datetime | None = None
    received_at: datetime | None = None
    payload: dict | None = None


class WhatsAppCloudConnector:
    provider = "whatsapp_cloud"
    token_env = "PARDHA_WHATSAPP_ACCESS_TOKEN"
    phone_number_id_env = "PARDHA_WHATSAPP_PHONE_NUMBER_ID"

    def _network_enabled(self) -> bool:
        return os.getenv("PARDHA_WHATSAPP_ENABLE_NETWORK", "false").lower() in {"1", "true", "yes"}

    def _configured(self) -> bool:
        return bool(os.getenv(self.token_env) and os.getenv(self.phone_number_id_env))

    def _unsupported_network(self) -> None:
        raise RuntimeError(
            "WhatsApp Business Cloud API calls are disabled or not implemented in this local connector. "
            "Set PARDHA_WHATSAPP_ENABLE_NETWORK=true with PARDHA_WHATSAPP_ACCESS_TOKEN and "
            "PARDHA_WHATSAPP_PHONE_NUMBER_ID when enabling live provider calls."
        )

    def send_message(self, from_phone: str, to_phone: str, body: str) -> WhatsAppProviderMessage:
        if self._network_enabled() and self._configured():
            self._unsupported_network()
        now = datetime.now(timezone.utc)
        return WhatsAppProviderMessage(
            provider_message_id=f"whatsapp-local-sent-{uuid4()}",
            sender_phone=from_phone,
            recipient_phone=to_phone,
            body=body,
            status="sent",
            sent_at=now,
            payload={"provider": self.provider, "mode": "local"},
        )

    def send_template(
        self,
        from_phone: str,
        to_phone: str,
        template_name: str,
        language: str,
        parameters: list[str],
        body: str,
    ) -> WhatsAppProviderMessage:
        if self._network_enabled() and self._configured():
            self._unsupported_network()
        now = datetime.now(timezone.utc)
        return WhatsAppProviderMessage(
            provider_message_id=f"whatsapp-local-template-{uuid4()}",
            sender_phone=from_phone,
            recipient_phone=to_phone,
            body=body,
            status="sent",
            message_type="template",
            template_name=template_name,
            sent_at=now,
            payload={
                "provider": self.provider,
                "mode": "local",
                "language": language,
                "parameters": parameters,
            },
        )


def get_connector(provider: str) -> WhatsAppCloudConnector:
    normalized = provider.strip().lower()
    if normalized in {"whatsapp_cloud", "meta_direct"}:
        return WhatsAppCloudConnector()
    if normalized == "twilio":
        return WhatsAppCloudConnector()
    raise ValueError(f"Unsupported WhatsApp provider: {provider}")
