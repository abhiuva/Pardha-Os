import os
import unittest

from fastapi.testclient import TestClient

from app.agents.cto import create_jira_engineering_task, link_jira_technical_task, update_jira_task_status
from app.agents.pm import create_jira_epic, create_jira_sprint_backlog, create_jira_story
from app.db import SessionLocal, init_db
from app.db.models import AgentCollaboration as AgentCollaborationModel
from app.db.models import Event as EventModel
from app.db.models import JiraIssue as JiraIssueModel
from app.db.models import JiraProject as JiraProjectModel
from app.db.models import JiraSyncHistory as JiraSyncHistoryModel
from app.db.models import Objective as ObjectiveModel
from app.db.models import Task as TaskModel
from app.jira.schemas import JiraSyncRequest
from app.jira.service import sync_jira
from app.main import app


class FakeJiraClient:
    def __init__(self):
        self.jira_url = "https://example.atlassian.net"
        self.email = "pm@example.com"
        self.project_key = "EAT"
        self.created = []
        self.updated = []

    def create_epic(self, summary, description=""):
        return self._create("EPIC", summary, description)

    def create_story(self, summary, description="", *, parent_key=None, technical=False):
        return self._create("TECH" if technical else "STORY", summary, description, parent_key)

    def update_issue(self, issue_key, fields):
        self.updated.append((issue_key, fields))
        return {"key": issue_key, "fields": fields}

    def transition_issue(self, issue_key, status):
        self.updated.append((issue_key, {"transition": status}))
        return {"key": issue_key, "fields": {"status": {"name": status}}}

    def get_issue(self, issue_key):
        return {"key": issue_key, "fields": {"status": {"name": "To Do"}}}

    def search_issues(self, jql, max_results=50):
        return {"issues": [], "jql": jql, "maxResults": max_results}

    def _create(self, prefix, summary, description, parent_key=None):
        key = f"{self.project_key}-{len(self.created) + 1}"
        issue = {
            "key": key,
            "fields": {
                "summary": summary,
                "description": description,
                "status": {"name": "To Do"},
            },
        }
        if parent_key:
            issue["fields"]["parent"] = {"key": parent_key}
        self.created.append((prefix, issue))
        return issue


class JiraConnectorTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        self._clear()

    def tearDown(self):
        self._clear()

    def _clear(self):
        with SessionLocal() as session:
            session.query(JiraSyncHistoryModel).delete()
            session.query(JiraIssueModel).delete()
            session.query(JiraProjectModel).delete()
            session.query(AgentCollaborationModel).delete()
            session.query(TaskModel).delete()
            session.query(ObjectiveModel).delete()
            session.query(EventModel).delete()
            session.commit()

    def test_pm_and_cto_agent_jira_helpers_delegate_to_client(self):
        fake = FakeJiraClient()

        epic = create_jira_epic("Launch EatOnTime", "Launch planning.", client=fake)
        story = create_jira_story("School onboarding", "As a school admin...", parent_key=epic["key"], client=fake)
        backlog = create_jira_sprint_backlog(
            [{"summary": "Menu import", "description": "Import cafeteria menus."}],
            epic_key=epic["key"],
            client=fake,
        )
        technical = create_jira_engineering_task("Build school setup API", "Implement setup.", parent_key=epic["key"], client=fake)
        updated = update_jira_task_status(technical["key"], "In Progress", client=fake)
        linked = link_jira_technical_task(technical["key"], epic["key"], client=fake)

        self.assertEqual(epic["key"], "EAT-1")
        self.assertEqual(story["fields"]["parent"]["key"], "EAT-1")
        self.assertEqual(backlog[0]["fields"]["parent"]["key"], "EAT-1")
        self.assertEqual(technical["fields"]["parent"]["key"], "EAT-1")
        self.assertEqual(updated["key"], technical["key"])
        self.assertEqual(updated["fields"]["status"]["name"], "In Progress")
        self.assertEqual(linked["fields"]["parent"]["key"], "EAT-1")
        self.assertEqual(len(fake.created), 4)
        self.assertEqual(len(fake.updated), 2)

    def test_sync_creates_eatontime_epic_stories_and_persists_jira_ids(self):
        fake = FakeJiraClient()

        result = sync_jira(
            JiraSyncRequest(
                title="Launch EatOnTime in 3 new schools",
                description="Coordinate product, onboarding, and engineering delivery for three new schools.",
                business_name="EatOnTime",
                priority="high",
            ),
            client=fake,
        )

        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.project_key, "EAT")
        self.assertIsNotNone(result.objective_id)
        self.assertEqual(result.epic.jira_issue_key, "EAT-1")
        self.assertEqual(len(result.stories), 3)
        self.assertEqual(len(result.technical_stories), 3)
        self.assertTrue(all(issue.parent_jira_issue_key == "EAT-1" for issue in result.stories + result.technical_stories))
        self.assertEqual(result.history.issue_count, 7)

        with SessionLocal() as session:
            self.assertEqual(session.query(JiraProjectModel).count(), 1)
            self.assertEqual(session.query(JiraIssueModel).count(), 7)
            self.assertEqual(session.query(JiraSyncHistoryModel).count(), 1)
            keys = {issue.jira_issue_key for issue in session.query(JiraIssueModel).all()}
            self.assertEqual(keys, {f"EAT-{index}" for index in range(1, 8)})
            objective = session.query(ObjectiveModel).one()
            self.assertEqual(objective.title, "Launch EatOnTime in 3 new schools")

    def test_jira_api_reports_status_projects_and_issues(self):
        fake = FakeJiraClient()
        sync_jira(
            JiraSyncRequest(
                title="Launch EatOnTime in 3 new schools",
                description="Create the Jira work items.",
                business_name="EatOnTime",
                priority="high",
            ),
            client=fake,
        )

        status = self.client.get("/jira/status").json()
        self.assertTrue(status["connected"])
        self.assertEqual(status["project_count"], 1)
        self.assertEqual(status["issue_count"], 7)
        self.assertEqual(status["epic_count"], 1)
        self.assertEqual(status["story_count"], 6)
        self.assertEqual(len(self.client.get("/jira/projects").json()), 1)
        self.assertEqual(len(self.client.get("/jira/issues").json()), 7)

    def test_jira_routes_are_registered_in_openapi(self):
        openapi = self.client.get("/openapi.json").json()

        self.assertIn("/jira/status", openapi["paths"])
        self.assertIn("/jira/projects", openapi["paths"])
        self.assertIn("/jira/issues", openapi["paths"])
        self.assertIn("/jira/sync", openapi["paths"])
        self.assertIn("get", openapi["paths"]["/jira/status"])
        self.assertIn("get", openapi["paths"]["/jira/projects"])
        self.assertIn("get", openapi["paths"]["/jira/issues"])
        self.assertIn("post", openapi["paths"]["/jira/sync"])

    def test_jira_sync_requires_configuration_for_real_client(self):
        old_env = {key: os.environ.get(key) for key in ["JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN", "JIRA_PROJECT_KEY"]}
        for key in old_env:
            os.environ.pop(key, None)
        try:
            response = self.client.post(
                "/jira/sync",
                json={
                    "title": "Missing config",
                    "description": "Should not call Jira.",
                    "business_name": "Pardha",
                    "priority": "medium",
                },
            )
            self.assertEqual(response.status_code, 503)
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value


if __name__ == "__main__":
    unittest.main()
