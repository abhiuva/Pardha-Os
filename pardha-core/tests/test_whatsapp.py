import unittest

from fastapi.testclient import TestClient

from app.agents.ceo import generate_daily_brief
from app.agents.pm import generate_pm_brief
from app.business.service import get_business_by_name
from app.db import SessionLocal, init_db
from app.db.models import WhatsAppAccount, WhatsAppConversation, WhatsAppMessage, WhatsAppTemplate
from app.main import app
from app.whatsapp.operations import notify_lunch_delivered
from app.whatsapp.service import (
    create_account,
    create_template,
    get_conversation,
    get_conversations,
    get_messages,
    receive_message,
    send_message,
    send_template,
    summarize_whatsapp,
)


class WhatsAppConnectorTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        self.client.post("/context/switch", json={"business_name": "DP360"})
        self._clear()

    def tearDown(self):
        self._clear()
        self.client.post("/context/switch", json={"business_name": "DP360"})

    def _clear(self):
        with SessionLocal() as session:
            session.query(WhatsAppMessage).delete()
            session.query(WhatsAppConversation).delete()
            session.query(WhatsAppTemplate).delete()
            session.query(WhatsAppAccount).delete()
            session.commit()

    def test_send_template_receive_and_conversation_history(self):
        business = get_business_by_name("EatOnTime")
        account = create_account(
            {
                "business_id": business.business_id,
                "phone_number": "+15550001111",
                "provider": "whatsapp_cloud",
            }
        )
        create_template(
            {
                "business_id": business.business_id,
                "account_id": account.account_id,
                "template_name": "lunch_delivered",
                "language": "en",
                "body": "Lunch delivered for {{1}}.",
            }
        )

        sent = send_template(
            {
                "business_id": business.business_id,
                "account_id": account.account_id,
                "to_phone": "+15550002222",
                "template_name": "lunch_delivered",
                "language": "en",
                "parameters": ["Order 42"],
            }
        )
        inbound = receive_message(
            {
                "business_id": business.business_id,
                "account_id": account.account_id,
                "from_phone": "+15550002222",
                "contact_name": "School Admin",
                "body": "Received. Lunch delivered successfully.",
            }
        )

        self.assertEqual(sent.message_type, "template")
        self.assertEqual(sent.status, "sent")
        self.assertEqual(inbound.direction, "inbound")
        conversations = get_conversations(business_id=business.business_id)
        self.assertEqual(len(conversations), 1)
        self.assertEqual(conversations[0].message_count, 2)
        self.assertEqual(len(get_conversation(conversations[0].conversation_id, business_id=business.business_id)), 2)
        summary = summarize_whatsapp(business_id=business.business_id)
        self.assertEqual(summary.message_volume, 2)
        self.assertIn("Lunch delivered for Order 42.", summary.operations_updates)

    def test_api_is_business_scoped(self):
        uva = get_business_by_name("UVA")
        dp360 = get_business_by_name("DP360")
        uva_account = create_account({"business_id": uva.business_id, "phone_number": "+155501"})
        dp360_account = create_account({"business_id": dp360.business_id, "phone_number": "+155502"})
        send_message(
            {
                "business_id": uva.business_id,
                "account_id": uva_account.account_id,
                "to_phone": "+155503",
                "body": "UVA executive summary update.",
            }
        )
        send_message(
            {
                "business_id": dp360.business_id,
                "account_id": dp360_account.account_id,
                "to_phone": "+155504",
                "body": "DP360 risk alert.",
            }
        )

        uva_messages = self.client.get("/whatsapp/messages", params={"business_id": uva.business_id}).json()
        dp360_messages = self.client.get("/whatsapp/messages", params={"business_id": dp360.business_id}).json()

        self.assertEqual(len(uva_messages), 1)
        self.assertIn("UVA", uva_messages[0]["body"])
        self.assertEqual(len(dp360_messages), 1)
        self.assertIn("DP360", dp360_messages[0]["body"])
        self.assertEqual(len(self.client.get("/whatsapp/accounts", params={"business_id": uva.business_id}).json()), 1)
        self.assertEqual(len(self.client.get("/whatsapp/conversations", params={"business_id": dp360.business_id}).json()), 1)

    def test_ceo_pm_and_operations_integration(self):
        business = get_business_by_name("EatOnTime")
        account = create_account({"business_id": business.business_id, "phone_number": "+155509"})
        notify_lunch_delivered(
            account_id=account.account_id,
            to_phone="+155510",
            order_ref="Order 77",
            business_id=business.business_id,
        )
        receive_message(
            {
                "business_id": business.business_id,
                "account_id": account.account_id,
                "from_phone": "+155510",
                "body": "Urgent risk: lunch delivery delay.",
            }
        )

        ceo = generate_daily_brief(business_id=business.business_id)
        pm = generate_pm_brief(business_id=business.business_id)

        self.assertEqual(ceo.whatsapp_summary["message_volume"], 2)
        self.assertTrue(ceo.whatsapp_risk_notifications)
        self.assertIn("Lunch delivered for Order 77.", pm.whatsapp_project_updates)


if __name__ == "__main__":
    unittest.main()
