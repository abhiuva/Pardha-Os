import unittest

from fastapi.testclient import TestClient

from app.collaboration.service import get_collaborations, get_objectives, get_tasks
from app.db import SessionLocal, init_db
from app.db.models import AgentCollaboration as AgentCollaborationModel
from app.db.models import Event as EventModel
from app.db.models import Objective as ObjectiveModel
from app.db.models import Task as TaskModel
from app.main import app


class CollaborationEngineTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        self.client.post("/context/switch", json={"business_name": "DP360"})
        self._clear()

    def tearDown(self):
        self._clear()
        self.client.post("/context/switch", json={"business_name": "DP360"})

    def _clear(self):
        with SessionLocal() as session:
            session.query(AgentCollaborationModel).delete()
            session.query(TaskModel).delete()
            session.query(ObjectiveModel).delete()
            session.query(EventModel).delete()
            session.commit()

    def test_creating_objective_runs_full_collaboration_workflow(self):
        response = self.client.post(
            "/objectives",
            json={
                "title": "Launch customer analytics",
                "description": "Deliver an MVP analytics workflow for customers.",
                "business_name": "EatOnTime",
                "priority": "high",
            },
        )

        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertEqual(result["objective"]["status"], "IN_PROGRESS")
        self.assertEqual(result["objective"]["business_name"], "EatOnTime")
        self.assertEqual(len(result["epics"]), 3)
        self.assertEqual(len(result["tasks"]), 6)
        engineering_tasks = [task for task in result["tasks"] if task["payload"]["work_type"] == "engineering"]
        self.assertEqual(len(engineering_tasks), 3)
        self.assertTrue(all(task["assigned_agent"] == "cto" for task in engineering_tasks))
        self.assertTrue(all(task["payload"]["technical_risks"] for task in engineering_tasks))
        self.assertEqual(len(result["collaborations"]), 14)
        self.assertEqual(
            [item["event_type"] for item in result["collaborations"]],
            [
                "OBJECTIVE_CREATED",
                "EPIC_CREATED", "TASK_CREATED",
                "EPIC_CREATED", "TASK_CREATED",
                "EPIC_CREATED", "TASK_CREATED",
                "TASK_CREATED", "TASK_ASSIGNED",
                "TASK_CREATED", "TASK_ASSIGNED",
                "TASK_CREATED", "TASK_ASSIGNED",
                "COLLABORATION_COMPLETED",
            ],
        )
        self.assertTrue(all(item["event_type"] for item in result["collaborations"]))
        self.assertTrue(all(item["timestamp"] for item in result["collaborations"]))

        with SessionLocal() as session:
            event_types = [event.event_type for event in session.query(EventModel).all()]
        self.assertEqual(event_types.count("OBJECTIVE_CREATED"), 1)
        self.assertEqual(event_types.count("EPIC_CREATED"), 3)
        self.assertEqual(event_types.count("TASK_CREATED"), 6)
        self.assertEqual(event_types.count("TASK_ASSIGNED"), 3)
        self.assertEqual(event_types.count("COLLABORATION_COMPLETED"), 1)

    def test_history_endpoints_return_persisted_pipeline(self):
        self.client.post(
            "/objectives",
            json={
                "title": "Improve reliability",
                "description": "Reduce incidents.",
                "business_name": "DP360",
                "priority": "critical",
            },
        )

        self.assertEqual(len(self.client.get("/objectives").json()), 1)
        objective_id = self.client.get("/objectives").json()[0]["objective_id"]
        self.assertEqual(len(self.client.get("/collaborations").json()), 14)
        self.assertEqual(len(self.client.get("/tasks").json()), 6)
        detail = self.client.get(f"/objectives/{objective_id}")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(len(detail.json()["tasks"]), 6)
        self.assertEqual(self.client.get("/objectives/missing").status_code, 404)
        self.assertEqual(len(get_objectives()), 1)
        self.assertEqual(len(get_collaborations()), 14)
        self.assertEqual(len(get_tasks()), 6)

    def test_invalid_objective_is_rejected_without_partial_workflow(self):
        response = self.client.post(
            "/objectives",
            json={"title": "", "description": "Invalid objective.", "business_name": "DP360", "priority": "medium"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(get_objectives(), [])
        self.assertEqual(get_collaborations(), [])
        self.assertEqual(get_tasks(), [])


if __name__ == "__main__":
    unittest.main()
