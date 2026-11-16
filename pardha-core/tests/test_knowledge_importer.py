import json
import os
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import Event as EventModel
from app.db.models import Knowledge as KnowledgeModel
from app.knowledge.importer import (
    clear_knowledge_imports,
    get_knowledge_imports,
    import_knowledge_file,
    start_knowledge_watcher,
    stop_knowledge_watcher,
)
from app.main import app


class KnowledgeImporterTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        stop_knowledge_watcher()
        with SessionLocal() as session:
            session.query(EventModel).delete()
            session.query(KnowledgeModel).delete()
            session.commit()
        clear_knowledge_imports()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        for folder in ("uva", "dp360", "eatontime", "trevia"):
            (self.root / folder).mkdir()

    def tearDown(self):
        stop_knowledge_watcher()
        with SessionLocal() as session:
            session.query(EventModel).delete()
            session.query(KnowledgeModel).delete()
            session.commit()
        clear_knowledge_imports()
        self.temp_dir.cleanup()

    def test_import_validates_maps_and_notifies_agents(self):
        file_path = self._write_document("dp360", "architecture.json", category="architecture")

        imported = import_knowledge_file(file_path, self.root)

        self.assertIsNotNone(imported)
        with SessionLocal() as session:
            knowledge = session.query(KnowledgeModel).one()
            events = session.query(EventModel).all()
        self.assertEqual(knowledge.category, "project")
        self.assertEqual(knowledge.document_metadata_json["original_category"], "architecture")
        self.assertEqual({event.target_agent for event in events}, {"ceo", "cto", "pm"})
        self.assertTrue(all(event.event_type == "KNOWLEDGE_ADDED" for event in events))

    def test_duplicate_file_and_duplicate_content_are_not_imported_twice(self):
        first = self._write_document("dp360", "first.json")
        second = self.root / "dp360" / "renamed.json"
        second.write_bytes(first.read_bytes())

        self.assertIsNotNone(import_knowledge_file(first, self.root))
        self.assertIsNone(import_knowledge_file(first, self.root))
        self.assertIsNone(import_knowledge_file(second, self.root))
        self.assertEqual(len(get_knowledge_imports()), 1)

    def test_invalid_document_is_rejected_without_persisting_data(self):
        file_path = self.root / "dp360" / "invalid.json"
        file_path.write_text(json.dumps({"business_name": "DP360", "category": "product"}))

        with self.assertRaises(ValueError):
            import_knowledge_file(file_path, self.root)

        self.assertEqual(get_knowledge_imports(), [])
        with SessionLocal() as session:
            self.assertEqual(session.query(KnowledgeModel).count(), 0)
            self.assertEqual(session.query(EventModel).count(), 0)

    def test_import_history_endpoint(self):
        import_knowledge_file(self._write_document("uva", "profile.json"), self.root)

        response = TestClient(app).get("/knowledge/imports")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["file_path"], "uva/profile.json")

    def test_watcher_automatically_imports_new_json_file(self):
        with patch.dict(
            os.environ,
            {
                "PARDHA_KNOWLEDGE_ROOT": str(self.root),
                "PARDHA_KNOWLEDGE_WATCHER_ENABLED": "true",
            },
        ):
            start_knowledge_watcher()
            self._write_document("dp360", "dropped.json")
            for _ in range(50):
                if get_knowledge_imports():
                    break
                time.sleep(0.05)

        self.assertEqual(len(get_knowledge_imports()), 1)

    def _write_document(self, folder: str, name: str, category: str = "product") -> Path:
        path = self.root / folder / name
        path.write_text(
            json.dumps(
                {
                    "business_name": folder.upper(),
                    "category": category,
                    "title": f"{folder} knowledge",
                    "version": "1.0",
                    "content": {"overview": "Structured business knowledge"},
                    "tags": [folder],
                    "source": "test",
                }
            )
        )
        return path


if __name__ == "__main__":
    unittest.main()
