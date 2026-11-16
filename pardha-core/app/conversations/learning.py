from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from app.db import SessionLocal
from app.db.models import FounderOperationalLearning


def record_operational_learning(
    *,
    owner: str,
    business_id: str | None,
    conversation_id: str,
    message: str,
    intent: str,
    capability_ids: list[str],
) -> None:
    now = datetime.now(timezone.utc)
    signals = _signals(message=message, intent=intent, capability_ids=capability_ids)
    if business_id:
        signals.append(
            {
                "signal_type": "preferred_business",
                "signal_key": business_id,
                "signal_value": {"business_id": business_id, "source": "conversation"},
                "confidence": 70,
            }
        )
    with SessionLocal() as session:
        for signal in signals:
            existing = (
                session.query(FounderOperationalLearning)
                .filter(
                    FounderOperationalLearning.owner == owner,
                    FounderOperationalLearning.business_id == business_id,
                    FounderOperationalLearning.signal_type == signal["signal_type"],
                    FounderOperationalLearning.signal_key == signal["signal_key"],
                )
                .one_or_none()
            )
            if existing:
                existing.signal_value = _merge(existing.signal_value or {}, signal["signal_value"])
                existing.confidence = min(100, max(existing.confidence, signal["confidence"]) + 2)
                existing.source_conversation_id = conversation_id
                existing.updated_at = now
            else:
                session.add(
                    FounderOperationalLearning(
                        learning_id=str(uuid4()),
                        owner=owner,
                        business_id=business_id,
                        signal_type=signal["signal_type"],
                        signal_key=signal["signal_key"],
                        signal_value=signal["signal_value"],
                        confidence=signal["confidence"],
                        source_conversation_id=conversation_id,
                        created_at=now,
                        updated_at=now,
                    )
                )
        session.commit()


def _signals(*, message: str, intent: str, capability_ids: list[str]) -> list[dict[str, Any]]:
    text = message.lower()
    signals: list[dict[str, Any]] = [
        {
            "signal_type": "frequent_intent",
            "signal_key": intent,
            "signal_value": {"intent": intent, "last_message": message[:240]},
            "confidence": 65,
        }
    ]
    for capability_id in capability_ids[:6]:
        signals.append(
            {
                "signal_type": "frequent_capability",
                "signal_key": capability_id,
                "signal_value": {"capability_id": capability_id, "intent": intent},
                "confidence": 62,
            }
        )
    if any(term in text for term in ("daily", "morning", "brief", "summary")):
        signals.append(
            {
                "signal_type": "daily_workflow",
                "signal_key": "executive_briefing",
                "signal_value": {"preference": "executive_briefing", "trigger": message[:240]},
                "confidence": 68,
            }
        )
    if any(term in text for term in ("approve", "approval", "reject", "modify")):
        signals.append(
            {
                "signal_type": "approval_pattern",
                "signal_key": "explicit_review",
                "signal_value": {"preference": "explicit_review", "trigger": message[:240]},
                "confidence": 66,
            }
        )
    return signals


def _merge(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    merged.update(incoming)
    merged["observations"] = int(existing.get("observations", 0)) + 1
    return merged
