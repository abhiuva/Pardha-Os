import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_marketing_cockpit.db")
os.environ.setdefault("PARDHA_CONNECTOR_MODE", "mock")
os.environ.setdefault("PARDHA_OLLAMA_ENABLED", "false")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import MarketingAnalytics, MarketingCampaign, SalesCompany, SalesContact, SalesDeal, SalesDemoBooking, SalesLead, SalesLeadQualification
from app.main import app
from app.sales.service import build_prospect_research, list_leads


class MarketingCockpitTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        with SessionLocal() as session:
            session.query(MarketingAnalytics).delete()
            session.query(MarketingCampaign).delete()
            session.query(SalesDemoBooking).delete()
            session.query(SalesLeadQualification).delete()
            session.query(SalesDeal).delete()
            session.query(SalesLead).delete()
            session.query(SalesContact).delete()
            session.query(SalesCompany).delete()
            session.commit()

    def test_kpi_api_returns_stable_mock_schema_and_zero_safe_calculations(self):
        response = self.client.get("/marketing/kpis")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "mock_contract")
        self.assertGreater(payload["impressions"], 0)
        self.assertGreater(payload["clicks"], 0)
        self.assertGreater(payload["leads"], 0)
        self.assertIn("cac", payload)
        self.assertIn("roas", payload)
        self.assertTrue(payload["funnel"])
        self.assertTrue(payload["sources"])
        self.assertGreaterEqual(payload["ctr"], 0)
        self.assertGreaterEqual(payload["cpc"], 0)

    def test_kpi_api_combines_sales_funnel_and_supports_source_filter(self):
        build_prospect_research("I want 3 eCommerce prospects", target_count=3, industries=["eCommerce"])
        lead_id = list_leads()[0].lead_id
        self.client.post(
            f"/sales/leads/{lead_id}/qualify",
            json={"business_type": "eCommerce", "location": "US", "stage": "growth", "budget": 60000, "timeline": "this month", "requirement": "Improve retention", "source": "inbound demo"},
        )
        slot = self.client.get("/sales/calendar/availability?days=1").json()["slots"][0]["start"]
        self.client.post(f"/sales/leads/{lead_id}/demo-booking", json={"requested_slot": slot})

        response = self.client.get("/marketing/kpis?source=Meta%20Ads")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["filters"]["source"], "Meta Ads")
        self.assertGreaterEqual(payload["qualified_leads"], 1)
        self.assertGreaterEqual(payload["demos_booked"], 1)
        self.assertTrue(all(row["source"] == "Meta Ads" for row in payload["sources"]))

    def test_campaign_health_recommendations_are_approval_gated_and_not_auto_executed(self):
        self.client.get("/marketing/kpis")
        response = self.client.get("/marketing/campaign-health")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["policy"]["external_writes"], "blocked_without_founder_approval")
        self.assertFalse(payload["policy"]["recommendations_auto_execute"])
        self.assertTrue(payload["rows"])
        recommendation = payload["recommendations"][0]
        self.assertIn(recommendation["health"], {"green", "yellow", "red"})
        self.assertIn("reason", recommendation)
        self.assertFalse(recommendation["auto_execute"])
        if recommendation["action"] in {"pause", "scale", "change_creative", "change_audience"}:
            self.assertTrue(recommendation["approval_required"])


if __name__ == "__main__":
    unittest.main()
