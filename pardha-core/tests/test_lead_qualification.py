import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_lead_qualification.db")
os.environ.setdefault("PARDHA_CONNECTOR_MODE", "mock")
os.environ.setdefault("PARDHA_OLLAMA_ENABLED", "false")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import Event as EventModel
from app.db.models import SalesActivity as SalesActivityModel
from app.db.models import SalesCompany as SalesCompanyModel
from app.db.models import SalesContact as SalesContactModel
from app.db.models import SalesDeal as SalesDealModel
from app.db.models import SalesLead as SalesLeadModel
from app.db.models import SalesLeadQualification as SalesLeadQualificationModel
from app.main import app
from app.sales.service import build_prospect_research, list_leads


class LeadQualificationTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        with SessionLocal() as session:
            session.query(SalesLeadQualificationModel).delete()
            session.query(EventModel).delete()
            session.query(SalesActivityModel).delete()
            session.query(SalesDealModel).delete()
            session.query(SalesLeadModel).delete()
            session.query(SalesContactModel).delete()
            session.query(SalesCompanyModel).delete()
            session.commit()
        build_prospect_research("I want 3 eCommerce prospects", target_count=3, industries=["eCommerce"])

    def test_qualified_lead_triggers_demo_suggestion_and_hubspot_event(self):
        lead = list_leads()[0]

        response = self.client.post(
            f"/sales/leads/{lead.lead_id}/qualify",
            json={
                "business_type": "eCommerce",
                "location": "US",
                "stage": "growth",
                "budget": 60000,
                "timeline": "this month",
                "requirement": "Improve retention and repeat customer dashboard automation",
                "source": "inbound demo",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["qualification_status"], "qualified")
        self.assertGreaterEqual(payload["score"], 75)
        self.assertIn("demo booking", payload["recommendation"])
        self.assertEqual(payload["hubspot_event_payload"]["lead_score"], payload["score"])
        self.assertEqual(payload["hubspot_event_payload"]["qualification_status"], "qualified")

        refreshed = self.client.get("/sales/leads").json()[0]
        self.assertEqual(refreshed["qualification_status"], "qualified")
        self.assertEqual(refreshed["qualification_score"], payload["score"])

        with SessionLocal() as session:
            row = session.query(SalesLeadQualificationModel).filter_by(lead_id=lead.lead_id).one()
            event = session.query(EventModel).filter_by(event_type="hubspot.lead_qualification_ready").one()

        self.assertEqual(row.score, payload["score"])
        self.assertEqual(row.qualification_status, "qualified")
        self.assertEqual(event.payload["lead_score"], payload["score"])
        self.assertEqual(event.payload["qualification_status"], "qualified")

    def test_low_quality_lead_is_nurtured_not_demoed(self):
        lead = list_leads()[0]

        response = self.client.post(
            f"/sales/leads/{lead.lead_id}/qualify",
            json={
                "business_type": "other",
                "location": "US",
                "stage": "research",
                "budget": 0,
                "timeline": "next year",
                "requirement": "unknown",
                "source": "cold list",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["qualification_status"], "nurture")
        self.assertIn("budget", payload["missing_fields"])
        self.assertIn("nurture", payload["recommendation"])
        self.assertNotIn("demo booking", payload["recommendation"])

    def test_missing_required_field_returns_validation_error(self):
        lead = list_leads()[0]

        response = self.client.post(
            f"/sales/leads/{lead.lead_id}/qualify",
            json={
                "business_type": "eCommerce",
                "location": "US",
                "stage": "growth",
                "budget": 60000,
                "timeline": "this month",
                "requirement": "Improve retention",
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
