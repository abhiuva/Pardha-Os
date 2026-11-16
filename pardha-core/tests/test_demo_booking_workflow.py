import os
import unittest
from datetime import datetime, timedelta, timezone

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_demo_booking_workflow.db")
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
from app.main import app
from app.sales.service import build_prospect_research, list_leads


class DemoBookingWorkflowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        with SessionLocal() as session:
            session.query(SalesDemoBookingModel).delete()
            session.query(SalesLeadQualificationModel).delete()
            session.query(EventModel).delete()
            session.query(SalesActivityModel).delete()
            session.query(SalesDealModel).delete()
            session.query(SalesLeadModel).delete()
            session.query(SalesContactModel).delete()
            session.query(SalesCompanyModel).delete()
            session.commit()
        build_prospect_research("I want 3 eCommerce prospects", target_count=3, industries=["eCommerce"])

    def test_calendar_mock_returns_available_slots(self):
        response = self.client.get("/sales/calendar/availability?days=2")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["mode"], "mock")
        self.assertEqual(len(payload["slots"]), 6)
        self.assertTrue(all(slot["available"] for slot in payload["slots"]))
        self.assertTrue(all(slot["source"] == "mock_calendar_adapter" for slot in payload["slots"]))

    def test_qualified_lead_can_create_booked_demo_request(self):
        lead_id = self._qualified_lead_id()
        slot = self.client.get("/sales/calendar/availability?days=1").json()["slots"][0]["start"]

        response = self.client.post(
            f"/sales/leads/{lead_id}/demo-booking",
            json={"requested_slot": slot, "meeting_url": "https://meet.pardha.local/dp360", "owner": "Founder"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["lead_id"], lead_id)
        self.assertEqual(payload["status"], "booked")
        self.assertEqual(payload["calendar_mode"], "mock")
        self.assertEqual(payload["meeting_url"], "https://meet.pardha.local/dp360")
        self.assertEqual(payload["hubspot_event_payload"]["demo_status"], "booked")

        with SessionLocal() as session:
            booking = session.get(SalesDemoBookingModel, payload["booking_id"])
            lead = session.get(SalesLeadModel, lead_id)
            event = session.query(EventModel).filter_by(event_type="hubspot.demo_activity_ready").one()

        self.assertEqual(booking.status, "booked")
        self.assertEqual(lead.status, "demo_scheduled")
        self.assertEqual(event.payload["booking_id"], payload["booking_id"])

    def test_unqualified_lead_cannot_create_demo_booking(self):
        lead_id = list_leads()[0].lead_id
        slot = self.client.get("/sales/calendar/availability?days=1").json()["slots"][0]["start"]

        response = self.client.post(f"/sales/leads/{lead_id}/demo-booking", json={"requested_slot": slot})

        self.assertEqual(response.status_code, 400)
        self.assertIn("qualified", response.json()["detail"])

    def test_invalid_slot_is_rejected(self):
        lead_id = self._qualified_lead_id()
        invalid = (datetime.now(timezone.utc) + timedelta(days=30)).replace(hour=3, minute=17, second=0, microsecond=0).isoformat()

        response = self.client.post(f"/sales/leads/{lead_id}/demo-booking", json={"requested_slot": invalid})

        self.assertEqual(response.status_code, 400)
        self.assertIn("not available", response.json()["detail"])

    def test_status_transition_to_completed_emits_hubspot_event(self):
        lead_id = self._qualified_lead_id()
        booking = self.client.post(f"/sales/leads/{lead_id}/demo-booking", json={}).json()
        slot = self.client.get("/sales/calendar/availability?days=1").json()["slots"][1]["start"]

        booked = self.client.post(
            f"/sales/demo-bookings/{booking['booking_id']}/status",
            json={"status": "booked", "scheduled_at": slot, "meeting_url": "https://meet.pardha.local/booked"},
        )
        completed = self.client.post(
            f"/sales/demo-bookings/{booking['booking_id']}/status",
            json={"status": "completed", "notes": "Demo completed; proposal requested."},
        )

        self.assertEqual(booked.status_code, 200)
        self.assertEqual(completed.status_code, 200)
        self.assertEqual(completed.json()["status"], "completed")

        with SessionLocal() as session:
            events = session.query(EventModel).filter_by(event_type="hubspot.demo_activity_ready").all()
            lead = session.get(SalesLeadModel, lead_id)

        self.assertEqual(len(events), 2)
        self.assertEqual({event.payload["demo_status"] for event in events}, {"booked", "completed"})
        self.assertEqual(lead.status, "demo_completed")

    def _qualified_lead_id(self) -> str:
        lead_id = list_leads()[0].lead_id
        response = self.client.post(
            f"/sales/leads/{lead_id}/qualify",
            json={
                "business_type": "eCommerce",
                "location": "US",
                "stage": "growth",
                "budget": 60000,
                "timeline": "this month",
                "requirement": "Improve retention and demo conversion",
                "source": "inbound demo",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["qualification_status"], "qualified")
        return lead_id


if __name__ == "__main__":
    unittest.main()
