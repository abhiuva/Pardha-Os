import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_meta_ad_approvals.db")
os.environ.setdefault("PARDHA_CONNECTOR_MODE", "mock")
os.environ.setdefault("PARDHA_OLLAMA_ENABLED", "false")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import AuditLog, Event as EventModel, MetaAdApproval as MetaAdApprovalModel
from app.main import app


class MetaAdApprovalTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        with SessionLocal() as session:
            session.query(AuditLog).filter(AuditLog.resource_type == "meta_ad_approval").delete()
            session.query(MetaAdApprovalModel).delete()
            session.query(EventModel).delete()
            session.commit()
        self.client.post("/demo/seed")

    def test_meta_write_request_creates_pending_approval_without_external_write(self):
        response = self.client.post(
            "/marketing/meta/actions",
            json={
                "action": "campaign.create",
                "campaign_name": "DP360 Cloud Kitchen Pilot Ads",
                "budget": 1500,
                "audience": {"segment": "cloud kitchen founders", "country": "India"},
                "creative": {"headline": "Run your kitchen from one command center"},
                "expected_goal": "Book 10 qualified demos",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "pending")
        self.assertTrue(payload["approval_required"])
        self.assertTrue(payload["external_write_blocked"])
        self.assertFalse(payload["external_write_attempted"])
        self.assertEqual(payload["budget"], 1500)
        self.assertEqual(payload["audience"]["segment"], "cloud kitchen founders")

        with SessionLocal() as session:
            approval = session.get(MetaAdApprovalModel, payload["approval_id"])
            event = session.query(EventModel).filter_by(event_type="META_AD_APPROVAL_REQUIRED").one()
            audit = session.query(AuditLog).filter_by(action="meta.ad_approval.requested").one()

        self.assertEqual(approval.status, "pending")
        self.assertEqual(event.payload["approval_id"], payload["approval_id"])
        self.assertEqual(audit.outcome, "blocked_pending_approval")
        self.assertFalse(audit.metadata_json["external_write_attempted"])

    def test_approved_meta_action_emits_audit_log(self):
        approval = self._request_action()

        response = self.client.post(
            f"/marketing/meta/approvals/{approval['approval_id']}/approve",
            json={"decided_by": "Founder", "comment": "Budget approved for demo campaign."},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "approved")
        self.assertFalse(payload["external_write_attempted"])
        self.assertEqual(payload["decided_by"], "Founder")

        with SessionLocal() as session:
            audit = session.query(AuditLog).filter_by(action="meta.ad_approval.approved").one()
            event = session.query(EventModel).filter_by(event_type="META_AD_APPROVAL_APPROVED").one()

        self.assertEqual(audit.approval_id, approval["approval_id"])
        self.assertEqual(audit.outcome, "approved")
        self.assertFalse(audit.metadata_json["external_write_attempted"])
        self.assertEqual(event.payload["campaign_name"], approval["campaign_name"])

    def test_rejected_meta_action_does_not_attempt_external_write(self):
        approval = self._request_action(action="campaign.pause")

        response = self.client.post(
            f"/marketing/meta/approvals/{approval['approval_id']}/reject",
            json={"decided_by": "Founder", "comment": "Hold until creative is reviewed."},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "rejected")
        self.assertTrue(payload["external_write_blocked"])
        self.assertFalse(payload["external_write_attempted"])

        with SessionLocal() as session:
            stored = session.get(MetaAdApprovalModel, approval["approval_id"])
            audit = session.query(AuditLog).filter_by(action="meta.ad_approval.rejected").one()

        self.assertEqual(stored.status, "rejected")
        self.assertEqual(stored.external_write_attempted, 0)
        self.assertFalse(audit.metadata_json["external_write_attempted"])

    def _request_action(self, action="campaign.create"):
        response = self.client.post(
            "/marketing/meta/actions",
            json={
                "action": action,
                "campaign_name": "DP360 Meta Approval Test",
                "budget": 900,
                "audience": {"segment": "eCommerce founders"},
                "creative": {"headline": "Pilot DP360"},
                "expected_goal": "Generate 5 demo requests",
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()


if __name__ == "__main__":
    unittest.main()
