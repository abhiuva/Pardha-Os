import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_copilot.db")

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


class FounderCopilotPlatformTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_customer_lifecycle_platform(self):
        onboarding = self.client.post(
            "/copilot/onboarding",
            json={
                "company_name": "Pilot Cloud Kitchen",
                "business_type": "foodtech",
                "description": "Cloud kitchen pilot customer.",
                "revenue_goal": 500000,
            },
        )
        self.assertEqual(onboarding.status_code, 200)
        onboarding_payload = onboarding.json()
        self.assertTrue(onboarding_payload["dashboard_ready"])
        self.assertLessEqual(onboarding_payload["estimated_minutes"], 15)
        business_id = onboarding_payload["business_id"]

        copilot = self.client.post(
            "/copilot/founder",
            json={"business_id": business_id, "prompt": "I want to increase repeat purchases by 20.", "priority": "high"},
        )
        self.assertIn(copilot.status_code, {200, 201})
        copilot_payload = copilot.json()
        self.assertTrue(copilot_payload["business_analysis"])
        self.assertTrue(copilot_payload["execution_plan"])
        self.assertTrue(copilot_payload["kpis"])
        self.assertTrue(copilot_payload["success_metrics"])

        bi = self.client.get(f"/copilot/business-intelligence?business_id={business_id}")
        self.assertEqual(bi.status_code, 200)
        bi_payload = bi.json()
        self.assertGreaterEqual(bi_payload["business_health_score"], 80)
        self.assertTrue(bi_payload["swot_analysis"])
        self.assertTrue(bi_payload["executive_recommendations"])

        workspace = self.client.get(f"/copilot/customer-workspace?business_id={business_id}")
        self.assertEqual(workspace.status_code, 200)
        workspace_payload = workspace.json()
        self.assertTrue(workspace_payload["company_profile"])
        self.assertTrue(workspace_payload["knowledge_base"])
        self.assertTrue(workspace_payload["objectives"])
        self.assertTrue(workspace_payload["tasks"])
        self.assertTrue(workspace_payload["executive_briefs"])
        self.assertTrue(workspace_payload["meeting_notes"])
        self.assertTrue(workspace_payload["timeline"])

        briefs = self.client.get(f"/copilot/executive-briefs?business_id={business_id}")
        self.assertEqual(briefs.status_code, 200)
        briefs_payload = briefs.json()
        self.assertIn("ceo", briefs_payload["daily"])
        self.assertIn("sales", briefs_payload["daily"])
        self.assertIn("marketing", briefs_payload["daily"])
        self.assertTrue(briefs_payload["weekly_executive_summary"])
        self.assertTrue(briefs_payload["monthly_business_review"])

        health = self.client.get(f"/copilot/health-dashboard?business_id={business_id}")
        self.assertEqual(health.status_code, 200)
        health_payload = health.json()
        self.assertIn("sales_pipeline", health_payload)
        self.assertIn("marketing_performance", health_payload)
        self.assertIn("engineering_velocity", health_payload)
        self.assertIn("ai_recommendations", health_payload)

        consultant = self.client.post("/copilot/consultant", json={"business_id": business_id, "question": "What should we improve next?"})
        self.assertEqual(consultant.status_code, 200)
        self.assertTrue(consultant.json()["recommendations"])

        library = self.client.get("/copilot/demo-library")
        self.assertEqual(library.status_code, 200)
        self.assertGreaterEqual(len(library.json()["templates"]), 4)

        demo = self.client.post("/copilot/demo-library/load", json={"template": "SaaS Startup"})
        self.assertEqual(demo.status_code, 200)
        self.assertTrue(demo.json()["insights"])

        presentation = self.client.get(f"/copilot/presentation?business_id={business_id}")
        self.assertEqual(presentation.status_code, 200)
        presentation_payload = presentation.json()
        self.assertTrue(presentation_payload["company_overview"])
        self.assertTrue(presentation_payload["business_health"])
        self.assertTrue(presentation_payload["execution_plan"])
        self.assertTrue(presentation_payload["roadmap"])

        readiness = self.client.get("/copilot/commercial-readiness")
        self.assertEqual(readiness.status_code, 200)
        readiness_payload = readiness.json()
        self.assertGreaterEqual(readiness_payload["overall_score"], 95)
        self.assertGreaterEqual(readiness_payload["pilot_readiness_score"], 95)


if __name__ == "__main__":
    unittest.main()
