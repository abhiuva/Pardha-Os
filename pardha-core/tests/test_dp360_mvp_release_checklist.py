import unittest
from pathlib import Path

from app.commercial.service import dp360_command_center
from app.db import init_db


class DP360MVPReleaseChecklistTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_release_checklist_documents_required_validation_gates(self):
        checklist = Path("app/docs/dp360-mvp-release-checklist.md")

        self.assertTrue(checklist.exists())
        text = checklist.read_text()
        for required in [
            "Backend Gate",
            "Frontend Gate",
            "Connector Contract Gate",
            "Smoke Gate",
            "./venv/bin/python -m unittest",
            "npm run build",
            "tests.test_sprint_001_dp360_mvp",
            "tests.test_hubspot_connector",
            "tests.test_meta_ingestion",
            "tests.test_demo_booking_workflow",
            "tests.test_post_demo_drafts",
            "tests.test_marketing_cockpit",
            "/commercial/dp360-command-center",
            "/commercial/connectors/status",
            "/marketing/kpis",
            "PARDHA_OLLAMA_ENABLED=false",
            "external writes are blocked",
        ]:
            self.assertIn(required, text)

    def test_command_center_exposes_release_validation_contract(self):
        payload = dp360_command_center()

        self.assertEqual(payload["testing"]["backend"], "python -m unittest")
        self.assertEqual(payload["testing"]["frontend"], "npm run build")
        self.assertEqual(payload["testing"]["connector_contract"], "tests.test_sprint_001_dp360_mvp")
        self.assertEqual(payload["testing"]["smoke"], "GET /api/commercial/dp360-command-center")
        self.assertFalse(payload["controls"]["ollama_required"])
        self.assertEqual(payload["controls"]["destructive_external_writes"], "blocked_without_founder_approval")


if __name__ == "__main__":
    unittest.main()
