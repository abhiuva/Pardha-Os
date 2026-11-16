import unittest

from fastapi.testclient import TestClient

from app.business.service import get_business_by_name
from app.collaboration.service import create_objective, get_objectives, get_tasks
from app.db import SessionLocal, init_db
from app.db.models import (
    AgentCollaboration as AgentCollaborationModel,
    Event as EventModel,
    Knowledge as KnowledgeModel,
    Objective as ObjectiveModel,
    Task as TaskModel,
)
from app.knowledge.service import create_knowledge
from app.main import app


class BusinessContextTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        self.client.post("/context/switch", json={"business_name": "DP360"})
        self._clear_business_data()

    def tearDown(self):
        self._clear_business_data()
        self.client.post("/context/switch", json={"business_name": "DP360"})

    def _clear_business_data(self):
        with SessionLocal() as session:
            session.query(AgentCollaborationModel).delete()
            session.query(TaskModel).delete()
            session.query(ObjectiveModel).delete()
            session.query(EventModel).delete()
            session.query(KnowledgeModel).delete()
            session.commit()

    def test_default_businesses_and_context_switch_endpoint(self):
        response = self.client.get("/businesses")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            {"UVA", "DP360", "EatOnTime", "Trevia EV"}.issubset(
                {business["business_name"] for business in response.json()}
            )
        )
        uva = next(business for business in response.json() if business["business_name"] == "UVA")

        switched = self.client.post("/context/switch", json={"business_id": uva["business_id"]})

        self.assertEqual(switched.status_code, 200)
        self.assertEqual(switched.json()["active_business"]["business_name"], "UVA")
        self.assertEqual(self.client.get("/context/current").json()["active_business"]["business_name"], "UVA")

    def test_objectives_tasks_events_and_ceo_briefs_are_business_isolated(self):
        uva = get_business_by_name("UVA")
        eatontime = get_business_by_name("EatOnTime")
        self.assertIsNotNone(uva)
        self.assertIsNotNone(eatontime)

        create_knowledge(
            {
                "business_id": uva.business_id,
                "business_name": "UVA",
                "category": "roadmap",
                "title": "UVA onboarding",
                "content": "Build UVA onboarding analytics.",
                "source": "test",
            }
        )
        create_knowledge(
            {
                "business_id": eatontime.business_id,
                "business_name": "EatOnTime",
                "category": "roadmap",
                "title": "EatOnTime schools",
                "content": "Launch EatOnTime in 3 new schools.",
                "source": "test",
            }
        )

        create_objective(
            {
                "title": "Improve UVA admissions visibility",
                "description": "Give UVA leadership clean admissions signals.",
                "business_name": "UVA",
                "priority": "high",
            }
        )
        create_objective(
            {
                "title": "Launch EatOnTime in 3 new schools",
                "description": "Coordinate school launch operations.",
                "priority": "high",
            }
        )

        self.assertEqual([item.business_name for item in get_objectives(business_id=uva.business_id)], ["UVA"])
        self.assertEqual([item.business_name for item in get_objectives(business_id=eatontime.business_id)], ["EatOnTime"])
        self.assertTrue(all(task.business_id == uva.business_id for task in get_tasks(business_id=uva.business_id)))
        self.assertTrue(all(task.business_id == eatontime.business_id for task in get_tasks(business_id=eatontime.business_id)))

        uva_brief = self.client.get(f"/agents/ceo/brief?business_id={uva.business_id}").json()
        eatontime_brief = self.client.get(f"/agents/ceo/brief?business_id={eatontime.business_id}").json()
        uva_payload = str(uva_brief)
        eatontime_payload = str(eatontime_brief)

        self.assertIn("UVA", uva_payload)
        self.assertNotIn("EatOnTime", uva_payload)
        self.assertIn("EatOnTime", eatontime_payload)
        self.assertNotIn("UVA", eatontime_payload)

    def test_objective_without_business_name_routes_by_title(self):
        result = create_objective(
            {
                "title": "Launch EatOnTime in 3 new schools",
                "description": "Start food operations for three schools.",
                "priority": "medium",
            }
        )

        self.assertEqual(result.objective.business_name, "EatOnTime")
        self.assertTrue(all(task.business_id == result.objective.business_id for task in result.tasks))


if __name__ == "__main__":
    unittest.main()
