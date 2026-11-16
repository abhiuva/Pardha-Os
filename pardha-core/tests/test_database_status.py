import unittest

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app
from app.system.database import PARDHA_TABLES


class DatabaseStatusTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_status_reports_connection_tables_and_counts(self):
        response = self.client.get("/system/database/status")

        self.assertEqual(response.status_code, 200)
        status = response.json()
        self.assertTrue(status["connected"])
        self.assertTrue(set(PARDHA_TABLES).issubset(status["tables_found"]))
        self.assertEqual(set(status["record_counts"]), set(PARDHA_TABLES))
        self.assertTrue(all(isinstance(count, int) for count in status["record_counts"].values()))
        self.assertIn(status["scheduler_status"], {"running", "stopped"})
        self.assertIn(status["knowledge_import_status"], {"running", "stopped"})
        self.assertIn("active", status["agent_status"])
        self.assertIn("registered", status["agent_status"])


if __name__ == "__main__":
    unittest.main()
