import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_post_demo_drafts.db")
os.environ.setdefault("PARDHA_CONNECTOR_MODE", "mock")
os.environ.setdefault("PARDHA_OLLAMA_ENABLED", "false")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import Event as EventModel
from app.db.models import SalesActivity as SalesActivityModel
from app.db.models import SalesCompany as SalesCompanyModel
from app.db.models import SalesContact as SalesContactModel
from app.db.models import SalesDeal as SalesDealModel
from app.db.models import SalesDemoBooking as SalesDemoBookingModel
from app.db.models import SalesLead as SalesLeadModel
from app.db.models import SalesLeadQualification as SalesLeadQualificationModel
from app.db.models import SalesPostDemoDraft as SalesPostDemoDraftModel
from app.main import app
from app.sales.service import build_prospect_research, list_leads


class PostDemoDraftTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        with SessionLocal() as session:
            session.query(SalesPostDemoDraftModel).delete()
            session.query(SalesDemoBookingModel).delete()
            session.query(SalesLeadQualificationModel).delete()
            session.query(EventModel).delete()
            session.query(SalesActivityModel).delete()
            session.query(SalesDealModel).delete()
            session.query(SalesLeadModel).delete()
            session.query(SalesContactModel).delete()
            session.query(SalesCompanyModel).delete()
            session.commit()
        build_prospect_research("I want 2 eCommerce prospects", target_count=2, industries=["eCommerce"])

    def test_completed_demo_generates_approval_gated_follow_up_and_proposal(self):
        booking_id = self._completed_booking_id()

        response = self.client.post(
            f"/sales/demo-bookings/{booking_id}/post-demo-draft",
            json={
                "demo_summary": "Prospect needs retention visibility, qualified lead follow-up, and proposal tracking.",
                "pain_points": ["Low repeat purchase visibility", "Manual demo follow-up", "No proposal pipeline"],
                "decision_makers": ["Founder", "Head of Growth"],
                "next_action": "Review DP360 pilot proposal this week",
                "commercial_cta": "Approve a 30-day DP360 Commerce pilot",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["booking_id"], booking_id)
        self.assertEqual(payload["approval_status"], "pending")
        self.assertTrue(payload["external_send_blocked"])
        self.assertIn("Subject: DP360 next steps", payload["follow_up_email"])
        self.assertIn("Low repeat purchase visibility", payload["follow_up_email"])
        self.assertIn("DP360 fits", payload["dp360_fit"])
        self.assertIn("30-day DP360 Commerce pilot", payload["proposal_draft"])
        self.assertEqual(payload["hubspot_event_payload"]["approval_status"], "pending")

        with SessionLocal() as session:
            draft = session.get(SalesPostDemoDraftModel, payload["draft_id"])
            event = session.query(EventModel).filter_by(event_type="hubspot.post_demo_activity_ready").one()

        self.assertEqual(draft.approval_status, "pending")
        self.assertEqual(draft.external_send_blocked, 1)
        self.assertEqual(event.payload["draft_id"], payload["draft_id"])
        self.assertTrue(event.payload["external_send_blocked"])

    def test_incomplete_demo_cannot_generate_post_demo_draft(self):
        booking_id = self._booked_booking_id()

        response = self.client.post(
            f"/sales/demo-bookings/{booking_id}/post-demo-draft",
            json={"demo_summary": "Demo not completed yet."},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("completed demo", response.json()["detail"])

    def _qualified_lead_id(self) -> str:
        lead_id = list_leads()[0].lead_id
        response = self.client.post(
            f"/sales/leads/{lead_id}/qualify",
            json={
                "business_type": "eCommerce",
                "location": "US",
                "stage": "growth",
                "budget": 70000,
                "timeline": "this month",
                "requirement": "Improve retention and sales follow-up",
                "source": "inbound demo",
            },
        )
        self.assertEqual(response.status_code, 200)
        return lead_id

    def _booked_booking_id(self) -> str:
        lead_id = self._qualified_lead_id()
        slot = self.client.get("/sales/calendar/availability?days=1").json()["slots"][0]["start"]
        response = self.client.post(f"/sales/leads/{lead_id}/demo-booking", json={"requested_slot": slot})
        self.assertEqual(response.status_code, 200)
        return response.json()["booking_id"]

    def _completed_booking_id(self) -> str:
        booking_id = self._booked_booking_id()
        response = self.client.post(f"/sales/demo-bookings/{booking_id}/status", json={"status": "completed"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "completed")
        return booking_id


if __name__ == "__main__":
    unittest.main()
