import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_sales.db")

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


class SalesExecutiveTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_sales_executive_flow_generates_prospects_and_dashboard(self):
        prospect_response = self.client.post(
            "/sales/prospect",
            json={"query": "I want 50 eCommerce prospects", "target_count": 50, "industries": ["eCommerce"]},
        )

        self.assertEqual(prospect_response.status_code, 200)
        prospect_payload = prospect_response.json()
        self.assertEqual(prospect_payload["target_count"], 50)
        self.assertEqual(prospect_payload["industry"], "eCommerce")
        self.assertGreaterEqual(prospect_payload["generated_count"], 50)

        leads_response = self.client.get("/sales/leads")
        self.assertEqual(leads_response.status_code, 200)
        leads_payload = leads_response.json()
        self.assertGreaterEqual(len(leads_payload), 50)

        pipeline_response = self.client.get("/sales/pipeline")
        self.assertEqual(pipeline_response.status_code, 200)
        pipeline_payload = pipeline_response.json()
        self.assertTrue(pipeline_payload["stages"])
        self.assertGreaterEqual(pipeline_payload["total_value"], 0)

        demos_response = self.client.get("/sales/demos")
        self.assertEqual(demos_response.status_code, 200)
        demos_payload = demos_response.json()
        self.assertTrue(demos_payload["upcoming_demos"])

        summary_response = self.client.get("/sales/summary")
        self.assertEqual(summary_response.status_code, 200)
        summary_payload = summary_response.json()
        self.assertGreaterEqual(summary_payload["prospects"], 50)
        self.assertGreaterEqual(summary_payload["pipeline_value"], 0)
        self.assertGreaterEqual(summary_payload["upcoming_demos"], 1)

        lead_id = leads_payload[0]["lead_id"]

        outreach_response = self.client.get(f"/sales/leads/{lead_id}/outreach")
        self.assertEqual(outreach_response.status_code, 200)
        outreach_payload = outreach_response.json()
        self.assertIn("Subject:", outreach_payload["cold_email"])
        self.assertTrue(outreach_payload["linkedin_message"])
        self.assertTrue(outreach_payload["follow_up_email"])
        self.assertTrue(outreach_payload["meeting_request"])
        self.assertTrue(outreach_payload["proposal_request"])
        self.assertTrue(outreach_payload["demo_invitation"])
        self.assertEqual(outreach_payload["research_source"], "deterministic_icp_demo_dataset")
        self.assertEqual(outreach_payload["decision_maker_source"], "icp_role_template")

        scheduled_at = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        demo_response = self.client.post(
            f"/sales/leads/{lead_id}/schedule-demo",
            json={"scheduled_at": scheduled_at, "meeting_url": "https://meet.pardha.local/test", "owner": "Founder"},
        )
        self.assertEqual(demo_response.status_code, 200)
        demo_payload = demo_response.json()
        self.assertEqual(demo_payload["status"], "demo_scheduled")
        self.assertEqual(demo_payload["pipeline_stage"], "demo_scheduled")
        self.assertIn("BEGIN:VCALENDAR", demo_payload["calendar_invite_ics"])
        self.assertIn("SUMMARY:DP360 demo", demo_payload["calendar_invite_ics"])

        stage_response = self.client.post(f"/sales/leads/{lead_id}/stage", json={"status": "proposal_sent"})
        self.assertEqual(stage_response.status_code, 200)
        stage_payload = stage_response.json()
        self.assertEqual(stage_payload["status"], "proposal_sent")
        self.assertEqual(stage_payload["pipeline_stage"], "proposal_sent")

        missing_response = self.client.get("/sales/leads/missing-lead/outreach")
        self.assertEqual(missing_response.status_code, 404)

        invalid_stage_response = self.client.post(f"/sales/leads/{lead_id}/stage", json={"status": "invalid"})
        self.assertEqual(invalid_stage_response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
