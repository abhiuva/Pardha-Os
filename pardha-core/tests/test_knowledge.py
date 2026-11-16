import unittest

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import Knowledge as KnowledgeModel
from app.knowledge.service import (
    create_knowledge,
    get_knowledge,
    get_knowledge_by_business,
    search_knowledge,
)
from app.main import app


class KnowledgeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def setUp(self):
        with SessionLocal() as session:
            session.query(KnowledgeModel).delete()
            session.commit()
        self.client = TestClient(app)

    def tearDown(self):
        with SessionLocal() as session:
            session.query(KnowledgeModel).delete()
            session.commit()

    def test_create_knowledge(self):
        knowledge = create_knowledge(
            {
                "business_name": "UVA",
                "category": "company",
                "title": "UVA Capabilities",
                "content": (
                    "UVA provides Product Engineering, AI Solutions, Cloud Engineering "
                    "and Enterprise Software Development."
                ),
                "tags": ["engineering", "ai", "cloud"],
                "source": "company-profile",
            }
        )

        self.assertEqual(knowledge.business_name, "UVA")
        self.assertEqual(knowledge.category, "company")
        self.assertEqual(len(get_knowledge(business_name="UVA")), 1)
        self.assertIsNotNone(knowledge.knowledge_id)
        self.assertIsNotNone(knowledge.created_at)

    def test_search_knowledge_with_business_and_category_filters(self):
        self._create_samples()

        results = search_knowledge(query="charging", business_name="Trevia EV", category="product")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].title, "EV Charging Platform")

        response = self.client.get(
            "/knowledge/search",
            params={"query": "customer", "business_name": "EatOnTime", "category": "customer_feedback"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)

    def test_business_filtering_is_case_insensitive_and_isolated(self):
        self._create_samples()

        uva_items = get_knowledge_by_business("uva")
        self.assertEqual(len(uva_items), 1)
        self.assertTrue(all(item.business_name == "UVA" for item in uva_items))

        response = self.client.get("/knowledge/business/Trevia EV")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["business_name"], "Trevia EV")

    def test_api_create_and_category_validation(self):
        response = self.client.post(
            "/knowledge",
            json={
                "business_name": "UVA",
                "category": "company",
                "title": "UVA Overview",
                "content": "UVA provides Product Engineering and AI Solutions.",
                "tags": ["company"],
                "source": "manual",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["business_name"], "UVA")

        invalid = self.client.post(
            "/knowledge",
            json={
                "business_name": "UVA",
                "category": "invalid",
                "title": "Invalid",
                "content": "Invalid category.",
                "source": "manual",
            },
        )
        self.assertEqual(invalid.status_code, 422)

    def _create_samples(self):
        create_knowledge(
            {
                "business_name": "UVA",
                "category": "company",
                "title": "UVA Overview",
                "content": "UVA provides Product Engineering and AI Solutions.",
                "tags": ["engineering"],
                "source": "manual",
            }
        )
        create_knowledge(
            {
                "business_name": "Trevia EV",
                "category": "product",
                "title": "EV Charging Platform",
                "content": "Trevia EV aggregates charging stations for drivers.",
                "tags": ["charging", "ev"],
                "source": "product-team",
            }
        )
        create_knowledge(
            {
                "business_name": "EatOnTime",
                "category": "customer_feedback",
                "title": "Delivery Feedback",
                "content": "Customers want faster delivery status updates.",
                "tags": ["customer", "delivery"],
                "source": "support",
            }
        )


if __name__ == "__main__":
    unittest.main()
