import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.agents.cto import generate_cto_brief
from app.events.bus import Event
from app.main import app
from app.memory.engine import Memory
from app.projects.schemas import LargeModule, Project, ProjectAnalysis


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def make_event(event_id: str, event_type: str, payload: dict, source: str = "agent-a") -> Event:
    return Event(
        event_id=UUID(event_id),
        source_agent=source,
        target_agent="agent-b",
        event_type=event_type,
        payload=payload,
        timestamp=NOW,
    )


def make_memory(memory_id: str, content: str, metadata: dict | None = None) -> Memory:
    return Memory(
        memory_id=UUID(memory_id),
        agent_id="agent-a",
        content=content,
        metadata=metadata or {},
        timestamp=NOW,
    )


class CTOAgentTestCase(unittest.TestCase):
    def setUp(self):
        self.agents = [
            {"id": "agent-a", "name": "Alpha", "role": "engineering", "status": "active"},
            {"id": "agent-b", "name": "Beta", "role": "operations", "status": "active"},
        ]

    def test_classifies_persisted_events_memories_and_prioritizes_backlog(self):
        events = [
            make_event(
                "00000000-0000-0000-0000-000000000001",
                "product.requested",
                {"title": "Add team workspaces", "description": "Customer feature request"},
            ),
            make_event(
                "00000000-0000-0000-0000-000000000002",
                "bug.reported",
                {"title": "Checkout fails", "severity": "critical production outage"},
            ),
        ]
        memories = [
            make_memory(
                "00000000-0000-0000-0000-000000000003",
                "Database latency is increasing and needs monitoring.",
            ),
            make_memory(
                "00000000-0000-0000-0000-000000000004",
                "Refactor the event dispatch module.",
            ),
        ]

        with (
            patch("app.agents.cto.get_agents", return_value=self.agents),
            patch("app.agents.cto.get_events", return_value=events),
            patch("app.agents.cto.get_memories", return_value=memories),
        ):
            brief = generate_cto_brief()

        self.assertEqual([item.title for item in brief.product_requests], ["Add team workspaces"])
        self.assertTrue(any(item.category == "bug" for item in brief.open_engineering_tasks))
        self.assertTrue(any(item.category == "infrastructure" for item in brief.infrastructure_risks))
        self.assertTrue(any(item.category == "engineering_task" for item in brief.open_engineering_tasks))
        self.assertEqual(brief.prioritized_backlog[0].priority, "critical")
        self.assertEqual(brief.agent_activity[0].event_count, 2)
        self.assertEqual(brief.agent_activity[0].memory_count, 2)

    def test_empty_data_produces_deterministic_system_risks(self):
        with (
            patch("app.agents.cto.get_agents", return_value=[]),
            patch("app.agents.cto.get_events", return_value=[]),
            patch("app.agents.cto.get_memories", return_value=[]),
        ):
            first = generate_cto_brief()
            second = generate_cto_brief()

        self.assertEqual(first, second)
        self.assertEqual(first.open_engineering_tasks, [])
        self.assertEqual(first.product_requests, [])
        self.assertEqual(len(first.infrastructure_risks), 3)
        self.assertEqual(first.prioritized_backlog, [])

    def test_duplicate_signals_are_deduplicated(self):
        memories = [
            make_memory(
                "00000000-0000-0000-0000-000000000005",
                "Fix database deployment failure.",
            ),
            make_memory(
                "00000000-0000-0000-0000-000000000006",
                "Fix database deployment failure.",
            ),
        ]

        with (
            patch("app.agents.cto.get_agents", return_value=self.agents),
            patch("app.agents.cto.get_events", return_value=[]),
            patch("app.agents.cto.get_memories", return_value=memories),
        ):
            brief = generate_cto_brief()

        titles = [item.title for item in brief.open_engineering_tasks]
        self.assertEqual(titles.count("Fix database deployment failure."), 3)
        self.assertEqual(
            len([item for item in brief.open_engineering_tasks if item.category == "bug"]),
            1,
        )
        bug = next(item for item in brief.open_engineering_tasks if item.category == "bug")
        self.assertEqual(bug.source_id, "00000000-0000-0000-0000-000000000005")

    def test_cto_endpoint_returns_brief(self):
        with (
            patch("app.agents.cto.get_agents", return_value=self.agents),
            patch("app.agents.cto.get_events", return_value=[]),
            patch("app.agents.cto.get_memories", return_value=[]),
        ):
            response = TestClient(app).get("/agents/cto/brief")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("open_engineering_tasks", body)
        self.assertIn("product_requests", body)
        self.assertIn("infrastructure_risks", body)
        self.assertIn("recommended_actions", body)
        self.assertIn("prioritized_backlog", body)
        self.assertIn("agent_activity", body)
        self.assertIn("project_inventory", body)
        self.assertIn("project_findings", body)

    def test_project_inventory_identifies_repository_quality_gaps(self):
        project = Project(
            project_id="project-1",
            project_name="Large Project",
            project_path="/local/large-project",
            language="Python",
            framework="FastAPI",
            repository_summary="A local project.",
            analysis=ProjectAnalysis(
                folder_structure=["app/"],
                file_count=10,
                file_counts_by_extension={".py": 10},
                languages={"Python": 10},
                manifests=["requirements.txt"],
                has_readme=False,
                has_tests=False,
                has_docker=False,
                missing_documentation=["README", "docs directory"],
                missing_tests=["No test files or test directories detected."],
                large_modules=[LargeModule(path="app/main.py", lines=700)],
            ),
            last_scanned=NOW,
        )
        with (
            patch("app.agents.cto.get_agents", return_value=self.agents),
            patch("app.agents.cto.get_events", return_value=[]),
            patch("app.agents.cto.get_memories", return_value=[]),
            patch("app.agents.cto.get_projects", return_value=[project]),
        ):
            brief = generate_cto_brief()

        self.assertEqual(brief.project_inventory[0].project_name, "Large Project")
        self.assertTrue(any("missing documentation" in finding for finding in brief.project_findings))
        self.assertTrue(any("no tests" in finding for finding in brief.project_findings))
        self.assertTrue(any("large module" in finding for finding in brief.project_findings))


if __name__ == "__main__":
    unittest.main()
