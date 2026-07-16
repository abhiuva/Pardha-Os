import io
import os
import unittest
import zipfile

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_founder_experience_sprint5.db")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import Knowledge as KnowledgeModel
from app.db.models import KnowledgeImport as KnowledgeImportModel
from app.main import app


class FounderExperienceSprint5TestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        cls.business = next(item for item in cls.client.get("/businesses").json() if item["business_name"] == "DP360")

    def setUp(self):
        with SessionLocal() as session:
            session.query(KnowledgeImportModel).filter(KnowledgeImportModel.business_id == self.business["business_id"]).delete()
            session.query(KnowledgeModel).filter(KnowledgeModel.business_id == self.business["business_id"]).delete()
            session.commit()

    def test_docx_and_pptx_upload_extracts_searchable_knowledge(self):
        docx = _zip_bytes({"word/document.xml": _word_xml("DP360 repeat purchase playbook for enterprise commerce teams")})
        pptx = _zip_bytes({"ppt/slides/slide1.xml": _slide_xml("Cloud kitchen launch plan with school pilot execution")})

        response = self.client.post(
            "/knowledge/upload",
            data={
                "business_id": self.business["business_id"],
                "business_name": self.business["business_name"],
                "category": "company",
            },
            files=[
                ("files", ("repeat-playbook.docx", docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                ("files", ("school-pilots.pptx", pptx, "application/vnd.openxmlformats-officedocument.presentationml.presentation")),
            ],
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["uploaded"], 2)
        self.assertEqual(payload["duplicates"], 0)

        search = self.client.get(
            "/knowledge/search",
            params={"business_id": self.business["business_id"], "query": "school pilot"},
        )
        self.assertEqual(search.status_code, 200)
        self.assertTrue(any("school pilot execution" in item["content"] for item in search.json()))

    def test_connector_center_exposes_enterprise_integrations(self):
        response = self.client.get("/commercial/connectors/status")

        self.assertEqual(response.status_code, 200)
        providers = {item["provider"] for item in response.json()}
        self.assertTrue({"gmail", "outlook", "whatsapp", "jira", "google_calendar", "github", "vscode", "ollama"}.issubset(providers))

    def test_conversation_stream_supports_mission_control_states(self):
        response = self.client.post(
            "/conversations/stream",
            json={"business_id": self.business["business_id"], "message": "We need 5 pilot customers."},
        )

        self.assertEqual(response.status_code, 200)
        body = response.text
        for phase in ("thinking", "planning", "executing", "verifying", "completed"):
            self.assertIn(f'"phase": "{phase}"', body)


def _zip_bytes(files: dict[str, str]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for filename, content in files.items():
            archive.writestr(filename, content)
    return buffer.getvalue()


def _word_xml(text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body>
</w:document>"""


def _slide_xml(text: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<p:sld xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"
       xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
  <p:cSld><p:spTree><p:sp><p:txBody><a:p><a:r><a:t>{text}</a:t></a:r></a:p></p:txBody></p:sp></p:spTree></p:cSld>
</p:sld>"""


if __name__ == "__main__":
    unittest.main()
