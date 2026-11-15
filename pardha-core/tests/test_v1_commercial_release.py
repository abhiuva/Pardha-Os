import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_v1_release.db")
os.environ.setdefault("PARDHA_ADMIN_EMAIL", "founder@pardha.local")
TEST_PASSWORD = "test-" + "admin-" + "password"
os.environ.setdefault("PARDHA_ADMIN_PASSWORD", TEST_PASSWORD)

from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app


class V1CommercialReleaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def test_auth_knowledge_and_demo_release_flow(self):
        login = self.client.post(
            "/auth/login",
            json={"email": "founder@pardha.local", "password": TEST_PASSWORD, "remember_me": True},
        )
        self.assertEqual(login.status_code, 200)
        token = login.json()["token"]
        self.assertTrue(token)

        session = self.client.get("/auth/session", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(session.status_code, 200)
        self.assertTrue(session.json()["authenticated"])

        security = self.client.get("/auth/security")
        self.assertEqual(security.status_code, 200)
        security_payload = security.json()
        self.assertEqual(security_payload["password_hashing"], "pbkdf2_sha256")
        self.assertFalse(security_payload["plaintext_credentials_stored"])

        businesses = self.client.get("/businesses").json()
        dp360 = next(item for item in businesses if item["business_name"] == "DP360")

        upload = self.client.post(
            "/knowledge/upload",
            data={"business_id": dp360["business_id"], "business_name": "DP360", "category": "company"},
            files=[
                ("files", ("company.md", b"# DP360\nCustomer data platform context.", "text/markdown")),
                ("files", ("metrics.json", b'{"retention":"repeat purchase"}', "application/json")),
            ],
        )
        self.assertEqual(upload.status_code, 201)
        payload = upload.json()
        self.assertEqual(payload["uploaded"], 2)
        knowledge_id = payload["items"][0]["knowledge_id"]

        duplicate = self.client.post(
            "/knowledge/upload",
            data={"business_id": dp360["business_id"], "business_name": "DP360", "category": "company"},
            files=[("files", ("company.md", b"# DP360\nCustomer data platform context.", "text/markdown"))],
        )
        self.assertEqual(duplicate.status_code, 201)
        self.assertEqual(duplicate.json()["duplicates"], 1)

        imports = self.client.get("/knowledge/imports")
        self.assertEqual(imports.status_code, 200)
        self.assertGreaterEqual(len(imports.json()), 2)

        search = self.client.get(f"/knowledge/search?business_id={dp360['business_id']}&query=retention")
        self.assertEqual(search.status_code, 200)
        self.assertTrue(search.json())

        delete = self.client.delete(f"/knowledge/{knowledge_id}")
        self.assertEqual(delete.status_code, 200)
        self.assertTrue(delete.json()["deleted"])

        library = self.client.get("/copilot/demo-library")
        self.assertEqual(library.status_code, 200)
        names = {item["name"] for item in library.json()["templates"]}
        self.assertTrue({"DP360 Retail", "Cloud Kitchen", "E-commerce", "EatOnTime Demo"}.issubset(names))

        readiness = self.client.get("/copilot/commercial-readiness")
        self.assertEqual(readiness.status_code, 200)
        self.assertGreaterEqual(readiness.json()["overall_score"], 95)

        logout = self.client.post("/auth/logout", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(logout.status_code, 200)


if __name__ == "__main__":
    unittest.main()
