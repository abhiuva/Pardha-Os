import unittest

from app.db import SessionLocal, init_db
from app.db.models import Agent as AgentModel, Event as EventModel, Memory as MemoryModel
from app.events.bus import publish_event, get_events
from app.kernel.registry import get_agents, register_agent
from app.memory.engine import get_memories, save_memory


class DatabasePersistenceTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        with SessionLocal() as session:
            session.query(EventModel).delete()
            session.query(MemoryModel).delete()
            session.query(AgentModel).delete()
            session.commit()

    def test_agents_persist_in_database(self):
        agent = register_agent("Persistence", "testing")

        with SessionLocal() as session:
            retrieved = session.query(AgentModel).filter_by(id=agent["id"]).one_or_none()

        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Persistence")
        self.assertEqual(get_agents()[0]["id"], agent["id"])

    def test_events_persist_in_database(self):
        agent = register_agent("EventAgent", "source")
        event = publish_event({
            "source_agent": agent["id"],
            "target_agent": agent["id"],
            "event_type": "persist.test",
            "payload": {"value": 123},
        })

        with SessionLocal() as session:
            persisted = session.query(EventModel).filter_by(event_id=str(event.event_id)).one_or_none()

        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.event_type, "persist.test")
        self.assertEqual(len(get_events()), 1)

    def test_memories_persist_in_database(self):
        agent = register_agent("MemoryAgent", "source")
        memory = save_memory({
            "agent_id": agent["id"],
            "content": "Persist this memory.",
            "metadata": {"key": "value"},
        })

        with SessionLocal() as session:
            persisted = session.query(MemoryModel).filter_by(memory_id=str(memory.memory_id)).one_or_none()

        self.assertIsNotNone(persisted)
        self.assertEqual(persisted.content, "Persist this memory.")
        self.assertEqual(len(get_memories()), 1)


if __name__ == "__main__":
    unittest.main()
