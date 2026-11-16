import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import Project as ProjectModel
from app.main import app
from app.projects.service import analyze_project, get_projects, scan_project


class ProjectScannerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        with SessionLocal() as session:
            session.query(ProjectModel).delete()
            session.commit()
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "sample-project"
        self.root.mkdir()
        (self.root / "src").mkdir()
        (self.root / "tests").mkdir()
        (self.root / "README.md").write_text("# Sample Project")
        (self.root / "src" / "App.jsx").write_text("export default function App() { return null; }\n")
        (self.root / "tests" / "test_app.py").write_text("def test_app():\n    assert True\n")
        (self.root / "large.py").write_text("value = 1\n" * 510)
        (self.root / "package.json").write_text(
            json.dumps({"dependencies": {"react": "19.0.0"}, "devDependencies": {"vite": "8.0.0"}})
        )

    def tearDown(self):
        with SessionLocal() as session:
            session.query(ProjectModel).delete()
            session.commit()
        self.temp_dir.cleanup()

    def test_scan_project_persists_metadata_and_analysis(self):
        project = scan_project(str(self.root))

        self.assertEqual(project.project_name, "sample-project")
        self.assertEqual(project.language, "Python")
        self.assertIn("React", project.framework)
        self.assertTrue(project.analysis.has_readme)
        self.assertTrue(project.analysis.has_tests)
        self.assertEqual(project.analysis.large_modules[0].path, "large.py")
        self.assertEqual(len(get_projects()), 1)
        self.assertEqual(analyze_project(project.project_id).file_count, project.analysis.file_count)

    def test_rescan_updates_existing_project_without_duplicate(self):
        first = scan_project(str(self.root))
        (self.root / "src" / "extra.js").write_text("export const value = 1;\n")
        second = scan_project(str(self.root))

        self.assertEqual(first.project_id, second.project_id)
        self.assertEqual(len(get_projects()), 1)
        self.assertGreater(second.analysis.file_count, first.analysis.file_count)

    def test_project_endpoints(self):
        client = TestClient(app)
        response = client.post("/projects/scan", json={"project_path": str(self.root)})
        project_id = response.json()["project_id"]

        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(client.get("/projects").json()), 1)
        self.assertEqual(client.get(f"/projects/{project_id}").status_code, 200)
        self.assertEqual(client.get("/projects/missing").status_code, 404)
        self.assertEqual(client.post("/projects/scan", json={"project_path": "/missing/project"}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
