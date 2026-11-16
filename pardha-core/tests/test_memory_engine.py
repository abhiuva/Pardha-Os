import unittest

from fastapi.testclient import TestClient

from app.memory.engine import clear_memories
from app.main import app


class MemoryEngineTestCase(unittest.TestCase):
    def setUp(self):
        clear_memories()
        self.client = TestClient(app)

    def tearDown(self):
        clear_memories()

    def test_save_and_retrieve_memory(self):
        memory_data = {
            "agent_id": "agent-alpha",
            "content": "The agent learned the new prompt.",
            "metadata": {"source": "test"},
        }

        response = self.client.post("/memories", json=memory_data)
        self.assertEqual(response.status_code, 200)

        memory = response.json()
        self.assertEqual(memory["agent_id"], memory_data["agent_id"])
        self.assertEqual(memory["content"], memory_data["content"])
        self.assertEqual(memory["metadata"], memory_data["metadata"])
        self.assertIn("memory_id", memory)
        self.assertIn("timestamp", memory)

        response = self.client.get("/memories")
        self.assertEqual(response.status_code, 200)

        memories = response.json()
        self.assertEqual(len(memories), 1)
        self.assertEqual(memories[0]["memory_id"], memory["memory_id"])

    def test_search_memories(self):
        memory_a = {
            "agent_id": "agent-alpha",
            "content": "Learned local-first memory storage.",
            "metadata": {"topic": "storage"},
        }
        memory_b = {
            "agent_id": "agent-beta",
            "content": "Thoughts about agent collaboration.",
            "metadata": {"topic": "agents"},
        }

        self.client.post("/memories", json=memory_a)
        self.client.post("/memories", json=memory_b)

        response = self.client.get("/memories/search", params={"query": "storage"})
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["agent_id"], "agent-alpha")

    def test_get_memories_by_agent(self):
        memory_a = {
            "agent_id": "agent-alpha",
            "content": "First memory.",
        }
        memory_b = {
            "agent_id": "agent-beta",
            "content": "Second memory.",
        }

        self.client.post("/memories", json=memory_a)
        self.client.post("/memories", json=memory_b)

        response = self.client.get("/memories/agent-alpha")
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["agent_id"], "agent-alpha")

    def test_save_memory_validates_required_fields(self):
        response = self.client.post("/memories", json={"agent_id": "agent-alpha"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
