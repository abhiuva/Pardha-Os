import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID

from fastapi.testclient import TestClient

from app.agents.cto import TechnicalItem
from app.agents.pm import generate_pm_brief
from app.events.bus import Event
from app.main import app
from app.memory.engine import Memory


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def technical_item(title: str, category: str, priority: str, source_id: str) -> TechnicalItem:
    return TechnicalItem(
        title=title,
        category=category,
        priority=priority,
        source_type="event",
        source_id=source_id,
        source_agent="agent-a",
    )


class PMAgentTestCase(unittest.TestCase):
    def setUp(self):
        self.ceo_brief = SimpleNamespace(risks=["Customer activation is below target."])
        self.cto_brief = SimpleNamespace(
            prioritized_backlog=[
                technical_item("Fix critical checkout bug", "bug", "critical", "cto-1"),
                technical_item("Build MVP onboarding", "product_request", "medium", "cto-2"),
                technical_item("Upgrade database monitoring", "infrastructure", "high", "cto-3"),
            ],
            infrastructure_risks=[
                technical_item("Upgrade database monitoring", "infrastructure", "high", "cto-3"),
            ],
        )
        self.events = [
            Event(
                event_id=UUID("00000000-0000-0000-0000-000000000001"),
                source_agent="agent-a",
                target_agent="agent-b",
                event_type="roadmap.requested",
                payload={"title": "Launch customer analytics", "impact": "revenue growth"},
                timestamp=NOW,
            )
        ]
        self.memories = [
            Memory(
                memory_id=UUID("00000000-0000-0000-0000-000000000002"),
                agent_id="agent-a",
                content="Customer analytics is a roadmap priority.",
                metadata={"source": "research"},
                timestamp=NOW,
            )
        ]

    def _patch_inputs(self):
        return (
            patch("app.agents.pm.generate_daily_brief", return_value=self.ceo_brief),
            patch("app.agents.pm.generate_cto_brief", return_value=self.cto_brief),
            patch("app.agents.pm.get_events", return_value=self.events),
            patch("app.agents.pm.get_memories", return_value=self.memories),
        )

    def test_generates_prioritized_product_roadmap(self):
        patches = self._patch_inputs()
        with patches[0], patches[1], patches[2], patches[3]:
            brief = generate_pm_brief()

        self.assertEqual(brief.top_priorities[0].title, "Fix critical checkout bug")
        self.assertTrue(any(item.is_mvp for item in brief.product_backlog))
        self.assertTrue(any(item.roadmap_stage == "now" for item in brief.product_backlog))
        self.assertTrue(any(epic.name == "Reliability" for epic in brief.epics))
        self.assertTrue(any(epic.name == "Product Experience" for epic in brief.epics))
        self.assertIn("Customer activation is below target.", brief.risks)
        self.assertLessEqual(len(brief.recommended_next_sprint), 5)

    def test_deduplicates_product_context_across_sources(self):
        self.events[0].payload["title"] = "Build MVP onboarding"
        self.memories = []

        patches = self._patch_inputs()
        with patches[0], patches[1], patches[2], patches[3]:
            brief = generate_pm_brief()

        titles = [item.title for item in brief.product_backlog]
        self.assertEqual(titles.count("Build MVP onboarding"), 1)
        item = next(item for item in brief.product_backlog if item.title == "Build MVP onboarding")
        self.assertTrue(item.is_mvp)
        self.assertEqual(item.roadmap_stage, "now")

    def test_empty_context_is_deterministic(self):
        empty_ceo = SimpleNamespace(risks=[])
        empty_cto = SimpleNamespace(prioritized_backlog=[], infrastructure_risks=[])
        with (
            patch("app.agents.pm.generate_daily_brief", return_value=empty_ceo),
            patch("app.agents.pm.generate_cto_brief", return_value=empty_cto),
            patch("app.agents.pm.get_events", return_value=[]),
            patch("app.agents.pm.get_memories", return_value=[]),
        ):
            first = generate_pm_brief()
            second = generate_pm_brief()

        self.assertEqual(first, second)
        self.assertEqual(first.product_backlog, [])
        self.assertEqual(first.epics, [])
        self.assertIn("No product backlog could be generated from available business context.", first.risks)

    def test_pm_endpoint_returns_brief(self):
        patches = self._patch_inputs()
        with patches[0], patches[1], patches[2], patches[3]:
            response = TestClient(app).get("/agents/pm/brief")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertIn("top_priorities", body)
        self.assertIn("product_backlog", body)
        self.assertIn("epics", body)
        self.assertIn("risks", body)
        self.assertIn("recommended_next_sprint", body)


if __name__ == "__main__":
    unittest.main()
