import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_software_factory.db")
os.environ.setdefault("PARDHA_OLLAMA_ENABLED", "false")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import SoftwareFactoryApproval, SoftwareFactoryArtifact, SoftwareFactoryRequirement
from app.main import app


class SoftwareFactoryTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        cls.business = next(item for item in cls.client.get("/businesses").json() if item["business_name"] == "DP360")

    def setUp(self):
        with SessionLocal() as session:
            session.query(SoftwareFactoryApproval).filter(SoftwareFactoryApproval.business_id == self.business["business_id"]).delete()
            session.query(SoftwareFactoryArtifact).filter(SoftwareFactoryArtifact.business_id == self.business["business_id"]).delete()
            session.query(SoftwareFactoryRequirement).filter(SoftwareFactoryRequirement.business_id == self.business["business_id"]).delete()
            session.commit()

    def test_requirement_generates_complete_product_engineering_lifecycle(self):
        response = self.client.post(
            "/software-factory/requirements",
            json={"business_id": self.business["business_id"], "requirement": "We need QR tracking.", "requester": "Founder"},
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        artifact_types = {item["artifact_type"] for item in payload["artifacts"]}
        approval_types = {item["approval_type"] for item in payload["approvals"]}
        self.assertTrue(payload["requirement"]["discovery"]["clarification_required"])
        self.assertEqual(payload["requirement"]["status"], "waiting_approval")
        self.assertTrue({"prd", "architecture", "engineering_plan", "jira_orchestration", "development_context", "qa_plan", "release_package"}.issubset(artifact_types))
        self.assertTrue({"prd", "architecture", "engineering_plan", "jira_orchestration", "code_review", "release_package", "deployment"}.issubset(approval_types))
        self.assertFalse(payload["validation"]["production_code_written"])
        jira = next(item for item in payload["artifacts"] if item["artifact_type"] == "jira_orchestration")
        self.assertFalse(jira["content"]["live_jira_created"])
        self.assertIn("duplicate_prevention_key", jira["content"])

        with SessionLocal() as session:
            self.assertEqual(session.query(SoftwareFactoryRequirement).filter(SoftwareFactoryRequirement.business_id == self.business["business_id"]).count(), 1)
            self.assertGreaterEqual(session.query(SoftwareFactoryArtifact).filter(SoftwareFactoryArtifact.business_id == self.business["business_id"]).count(), 9)
            self.assertGreaterEqual(session.query(SoftwareFactoryApproval).filter(SoftwareFactoryApproval.business_id == self.business["business_id"]).count(), 7)

    def test_artifact_edit_approval_dashboard_validation_and_reverse_engineering(self):
        created = self.client.post(
            "/software-factory/requirements",
            json={"business_id": self.business["business_id"], "requirement": "Build customer retention dashboard in React and FastAPI."},
        ).json()
        prd = next(item for item in created["artifacts"] if item["artifact_type"] == "prd")
        approval = next(item for item in created["approvals"] if item["approval_type"] == "prd")

        edited_content = dict(prd["content"])
        edited_content["open_questions"] = ["Which retention cohort is highest priority?"]
        edited = self.client.patch(f"/software-factory/artifacts/{prd['artifact_id']}", json={"content": edited_content, "edited_by": "Founder"})
        self.assertEqual(edited.status_code, 200)
        self.assertEqual(edited.json()["version"], 2)

        approved = self.client.post(f"/software-factory/approvals/{approval['approval_id']}/approve", json={"decided_by": "Founder", "comment": "PRD approved."})
        self.assertEqual(approved.status_code, 200)
        self.assertEqual(next(item for item in approved.json()["approvals"] if item["approval_id"] == approval["approval_id"])["status"], "approved")

        dashboard = self.client.get(f"/software-factory/dashboard?business_id={self.business['business_id']}")
        self.assertEqual(dashboard.status_code, 200)
        self.assertGreaterEqual(dashboard.json()["open_stories"], 1)
        self.assertIn("release_readiness", dashboard.json())

        validation = self.client.get(f"/software-factory/validation?business_id={self.business['business_id']}")
        self.assertEqual(validation.status_code, 200)
        self.assertEqual(validation.json()["scenarios_run"], 100)
        self.assertEqual(validation.json()["score"], 100)

        reverse = self.client.post(
            "/software-factory/reverse-engineer",
            json={"business_id": self.business["business_id"], "target": "pardha-core", "target_type": "repository"},
        )
        self.assertEqual(reverse.status_code, 200)
        self.assertEqual(reverse.json()["target"], "pardha-core")
        self.assertTrue(reverse.json()["explanation"]["recommendations"])

    def test_software_factory_capabilities_are_registered(self):
        response = self.client.get("/capabilities/search", params={"query": "Generate PRD and architecture", "intent": "product_requirements"})
        self.assertEqual(response.status_code, 200)
        capability_ids = [item["capability"]["capability_id"] for item in response.json()["candidates"]]
        self.assertIn("software_factory.prd", capability_ids)


if __name__ == "__main__":
    unittest.main()
