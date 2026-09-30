import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_hubspot_connector.db")
os.environ.setdefault("PARDHA_CONNECTOR_MODE", "mock")
os.environ.setdefault("PARDHA_OLLAMA_ENABLED", "false")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import HubSpotSyncRecord as HubSpotSyncRecordModel
from app.db.models import SalesActivity as SalesActivityModel
from app.db.models import SalesCompany as SalesCompanyModel
from app.db.models import SalesContact as SalesContactModel
from app.db.models import SalesDeal as SalesDealModel
from app.db.models import SalesLead as SalesLeadModel
from app.main import app
from app.sales.service import build_prospect_research, list_leads


class FakeHubSpotClient:
    def __init__(self, fail=False):
        self.fail = fail

    def create_company(self, _payload):
        if self.fail:
            from app.hubspot.client import HubSpotClientError

            raise HubSpotClientError("temporary outage", retryable=True)
        return "company-123"

    def create_contact(self, _payload):
        return "contact-123"

    def create_deal(self, _payload):
        return "deal-123"


class HubSpotConnectorTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        with SessionLocal() as session:
            session.query(HubSpotSyncRecordModel).delete()
            session.query(SalesActivityModel).delete()
            session.query(SalesDealModel).delete()
            session.query(SalesLeadModel).delete()
            session.query(SalesContactModel).delete()
            session.query(SalesCompanyModel).delete()
            session.commit()
        build_prospect_research("I want 3 eCommerce prospects", target_count=3, industries=["eCommerce"])

    def test_lead_can_be_converted_to_hubspot_payload(self):
        lead = list_leads()[0]

        response = self.client.get(f"/hubspot/leads/{lead.lead_id}/payload")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["lead_id"], lead.lead_id)
        self.assertIn("email", payload["contact"])
        self.assertIn("name", payload["company"])
        self.assertIn("dealname", payload["deal"])

    def test_sync_creates_safe_mode_draft_by_default(self):
        lead = list_leads()[0]

        response = self.client.post("/hubspot/sync/lead", json={"lead_id": lead.lead_id, "allow_write": False})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["sync_status"], "draft")
        self.assertTrue(payload["safe_mode"])
        self.assertFalse(payload["duplicate"])

    def test_duplicate_detection_by_email(self):
        leads = list_leads()[:2]
        self.client.post("/hubspot/sync/lead", json={"lead_id": leads[0].lead_id, "allow_write": False})
        with SessionLocal() as session:
            contacts = session.query(SalesContactModel).filter(SalesContactModel.email.isnot(None)).limit(2).all()
            contacts[1].email = contacts[0].email
            session.commit()

        response = self.client.post("/hubspot/sync/lead", json={"lead_id": leads[1].lead_id, "allow_write": False})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["sync_status"], "duplicate")
        self.assertTrue(payload["duplicate"])

    def test_live_write_success_with_explicit_mode_and_permission(self):
        lead = list_leads()[0]
        self.client.post("/hubspot/config", json={"write_mode": "live"})
        with patch.dict(os.environ, {"PARDHA_CONNECTOR_MODE": "live", "HUBSPOT_ACCESS_TOKEN": "test-token"}, clear=False):
            from app.hubspot.service import sync_lead

            result = sync_lead(lead.lead_id, allow_write=True, client=FakeHubSpotClient())

        self.assertEqual(result.sync_status, "synced")
        self.assertFalse(result.safe_mode)
        self.assertEqual(result.hubspot_ids["company"], "company-123")

    def test_live_write_failure_records_retryable_error(self):
        lead = list_leads()[0]
        self.client.post("/hubspot/config", json={"write_mode": "live"})
        with patch.dict(os.environ, {"PARDHA_CONNECTOR_MODE": "live", "HUBSPOT_ACCESS_TOKEN": "test-token"}, clear=False):
            from app.hubspot.service import sync_lead

            result = sync_lead(lead.lead_id, allow_write=True, client=FakeHubSpotClient(fail=True))

        self.assertEqual(result.sync_status, "failed")
        self.assertTrue(result.retryable)
        self.assertIn("temporary outage", result.error)


if __name__ == "__main__":
    unittest.main()
