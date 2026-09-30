import os
import unittest
from unittest.mock import patch

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_meta_ingestion.db")
os.environ.setdefault("PARDHA_CONNECTOR_MODE", "mock")
os.environ.setdefault("PARDHA_OLLAMA_ENABLED", "false")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import Event as EventModel
from app.db.models import MarketingAnalytics as MarketingAnalyticsModel
from app.db.models import MarketingCampaign as MarketingCampaignModel
from app.db.models import MetaCampaignInsight as MetaCampaignInsightModel
from app.db.models import MetaConnectorConfig as MetaConnectorConfigModel
from app.main import app


class MetaIngestionTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        with SessionLocal() as session:
            session.query(MetaCampaignInsightModel).delete()
            session.query(MetaConnectorConfigModel).delete()
            session.query(MarketingAnalyticsModel).delete()
            session.query(MarketingCampaignModel).delete()
            session.query(EventModel).delete()
            session.commit()
        self.client.post("/demo/seed")

    def test_meta_mock_ingestion_normalizes_campaign_insights(self):
        response = self.client.post("/marketing/meta/ingest")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "mock_contract")
        self.assertEqual(payload["sync_status"], "mock")
        self.assertEqual(payload["rows_ingested"], 3)
        self.assertEqual(payload["status"]["authentication_status"], "mock_contract")
        self.assertTrue(all(row["spend"] >= 0 for row in payload["insights"]))
        self.assertTrue(all("reach" in row and "ctr" in row and "cpc" in row and "leads" in row for row in payload["insights"]))
        self.assertTrue(any(row["channel"] == "Instagram" for row in payload["insights"]))

    def test_meta_ingestion_persists_insights_and_updates_marketing_analytics(self):
        self.client.post("/marketing/meta/ingest")

        insights_response = self.client.get("/marketing/meta/insights")
        analytics_response = self.client.get("/marketing/analytics")

        self.assertEqual(insights_response.status_code, 200)
        self.assertEqual(analytics_response.status_code, 200)
        self.assertGreaterEqual(len(insights_response.json()), 3)
        channels = {row["channel"] for row in analytics_response.json()}
        self.assertIn("Meta Ads", channels)
        self.assertIn("Instagram", channels)

        with SessionLocal() as session:
            insight_count = session.query(MetaCampaignInsightModel).count()
            event = session.query(EventModel).filter_by(event_type="META_INSIGHTS_INGESTED").one()

        self.assertEqual(insight_count, 3)
        self.assertEqual(event.payload["rows"], 3)

    def test_live_mode_without_credentials_records_failure(self):
        with patch.dict(os.environ, {"PARDHA_CONNECTOR_MODE": "live"}, clear=False):
            os.environ.pop("META_ACCESS_TOKEN", None)
            os.environ.pop("META_AD_ACCOUNT_ID", None)
            response = self.client.post("/marketing/meta/ingest")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["sync_status"], "failed")
        self.assertEqual(payload["rows_ingested"], 0)
        self.assertIn("META_ACCESS_TOKEN", payload["status"]["missing_environment"])
        self.assertTrue(payload["insights"])
        self.assertEqual(payload["insights"][0]["sync_status"], "missing_credentials")


if __name__ == "__main__":
    unittest.main()
