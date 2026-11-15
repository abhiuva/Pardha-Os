import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_marketing.db")

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


class MarketingExecutiveTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_marketing_campaign_generates_workspace_content_calendar_and_dashboard(self):
        campaign_response = self.client.post(
            "/marketing/campaign",
            json={
                "prompt": "Launch campaign for cloud kitchens.",
                "industry": "Cloud Kitchens",
                "duration_days": 30,
                "budget": 25000,
                "channels": ["LinkedIn", "Google Ads", "Meta Ads", "Email Campaigns", "Website Content", "SEO", "Webinars"],
            },
        )

        self.assertEqual(campaign_response.status_code, 200)
        campaign_payload = campaign_response.json()
        self.assertEqual(campaign_payload["campaign"]["name"], "DP360 Cloud Kitchens Demand Generation")
        self.assertGreaterEqual(len(campaign_payload["content_calendar"]), 30)
        calendar_types = {item["content_type"] for item in campaign_payload["content_calendar"]}
        self.assertIn("weekly", calendar_types)
        self.assertIn("monthly", calendar_types)
        self.assertIn("quarterly", calendar_types)
        self.assertGreaterEqual(len(campaign_payload["content_assets"]), 10)
        self.assertGreaterEqual(len(campaign_payload["analytics"]), 7)

        content_types = {item["content_type"] for item in campaign_payload["content_assets"]}
        self.assertIn("linkedin_post", content_types)
        self.assertIn("landing_page", content_types)
        self.assertIn("google_ad", content_types)
        self.assertIn("email_1", content_types)
        self.assertIn("case_study", content_types)

        campaigns_response = self.client.get("/marketing/campaigns")
        self.assertEqual(campaigns_response.status_code, 200)
        self.assertGreaterEqual(len(campaigns_response.json()), 1)

        analytics_response = self.client.get("/marketing/analytics")
        self.assertEqual(analytics_response.status_code, 200)
        analytics_payload = analytics_response.json()
        self.assertTrue(all("ctr" in row and "cpl" in row and "roas" in row for row in analytics_payload))

        content_response = self.client.get("/marketing/content")
        self.assertEqual(content_response.status_code, 200)
        self.assertGreaterEqual(len(content_response.json()), 10)

        summary_response = self.client.get("/marketing/summary")
        self.assertEqual(summary_response.status_code, 200)
        summary_payload = summary_response.json()
        self.assertGreaterEqual(summary_payload["active_campaigns"], 1)
        self.assertGreater(summary_payload["impressions"], 0)
        self.assertGreater(summary_payload["leads"], 0)
        self.assertGreater(summary_payload["pipeline_contribution"], 0)
        self.assertTrue(summary_payload["recommendations"])
        self.assertTrue(summary_payload["next_actions"])

        dashboard_response = self.client.get("/marketing/dashboard")
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard_payload = dashboard_response.json()
        self.assertTrue(dashboard_payload["active_campaigns"])
        self.assertTrue(dashboard_payload["performance"])
        self.assertTrue(dashboard_payload["content_pipeline"])
        self.assertTrue(dashboard_payload["upcoming_campaigns"])

        ceo_response = self.client.get("/agents/ceo/brief")
        self.assertEqual(ceo_response.status_code, 200)
        ceo_payload = ceo_response.json()
        self.assertIn("marketing_summary", ceo_payload)
        self.assertTrue(ceo_payload["marketing_next_actions"])


if __name__ == "__main__":
    unittest.main()
