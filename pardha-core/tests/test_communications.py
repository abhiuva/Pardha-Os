import unittest

from fastapi.testclient import TestClient

from app.agents.ceo import generate_daily_brief
from app.agents.pm import generate_pm_brief
from app.business.service import get_business_by_name
from app.communications.service import create_account, create_draft, get_history, read_messages, search_messages, send_message
from app.db import SessionLocal, init_db
from app.db.models import CommunicationAccount, CommunicationHistory, Message, MessageThread
from app.main import app


class CommunicationsTestCase(unittest.TestCase):
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
            session.query(CommunicationHistory).delete()
            session.query(Message).delete()
            session.query(MessageThread).delete()
            session.query(CommunicationAccount).delete()
            session.commit()

    def test_configure_account_create_draft_send_and_search(self):
        business = get_business_by_name("UVA")
        account = create_account(
            {
                "business_id": business.business_id,
                "provider": "gmail",
                "account_name": "UVA Gmail",
                "email": "uva@example.com",
            }
        )

        draft = create_draft(
            {
                "business_id": business.business_id,
                "account_id": account.account_id,
                "recipients": ["stakeholder@example.com"],
                "subject": "UVA stakeholder update",
                "body": "Sprint report and next steps for UVA.",
            }
        )
        sent = send_message(
            {
                "business_id": business.business_id,
                "account_id": account.account_id,
                "recipients": ["customer@example.com"],
                "subject": "UVA pilot opportunity",
                "body": "Following up on the UVA pilot opportunity.",
            }
        )

        self.assertEqual(draft.status, "draft")
        self.assertEqual(sent.status, "sent")
        self.assertEqual(len(read_messages(business_id=business.business_id)), 2)
        self.assertEqual(search_messages("pilot", business_id=business.business_id)[0].message_id, sent.message_id)
        self.assertEqual([item.action for item in get_history(business_id=business.business_id)], ["send_message", "create_draft", "account_configured"])

    def test_api_is_business_scoped(self):
        uva = get_business_by_name("UVA")
        eatontime = get_business_by_name("EatOnTime")
        uva_account = create_account(
            {
                "business_id": uva.business_id,
                "provider": "gmail",
                "account_name": "UVA Gmail",
                "email": "uva@example.com",
            }
        )
        eatontime_account = create_account(
            {
                "business_id": eatontime.business_id,
                "provider": "outlook",
                "account_name": "EatOnTime Outlook",
                "email": "eatontime@example.com",
            }
        )
        send_message(
            {
                "business_id": uva.business_id,
                "account_id": uva_account.account_id,
                "recipients": ["lead@example.com"],
                "subject": "UVA proposal",
                "body": "UVA proposal details.",
            }
        )
        send_message(
            {
                "business_id": eatontime.business_id,
                "account_id": eatontime_account.account_id,
                "recipients": ["school@example.com"],
                "subject": "EatOnTime school launch",
                "body": "EatOnTime launch details.",
            }
        )

        uva_messages = self.client.get("/communications/messages", params={"business_id": uva.business_id}).json()
        eatontime_messages = self.client.get("/communications/messages", params={"business_id": eatontime.business_id}).json()

        self.assertEqual(len(uva_messages), 1)
        self.assertEqual(uva_messages[0]["subject"], "UVA proposal")
        self.assertEqual(len(eatontime_messages), 1)
        self.assertEqual(eatontime_messages[0]["subject"], "EatOnTime school launch")
        self.assertEqual(len(self.client.get("/communications/accounts", params={"business_id": uva.business_id}).json()), 1)
        self.assertEqual(len(self.client.get("/communications/threads", params={"business_id": eatontime.business_id}).json()), 1)

    def test_ceo_and_pm_include_communication_signals(self):
        business = get_business_by_name("DP360")
        account = create_account(
            {
                "business_id": business.business_id,
                "provider": "gmail",
                "account_name": "DP360 Gmail",
                "email": "dp360@example.com",
            }
        )
        send_message(
            {
                "business_id": business.business_id,
                "account_id": account.account_id,
                "recipients": ["customer@example.com"],
                "subject": "DP360 pilot opportunity",
                "body": "Please reply with next steps for the pilot opportunity.",
            }
        )

        ceo = generate_daily_brief(business_id=business.business_id)
        pm = generate_pm_brief(business_id=business.business_id)

        self.assertEqual(ceo.inbox_summary["sent_count"], 1)
        self.assertIn("DP360 pilot opportunity", ceo.communication_opportunities)
        self.assertIn("DP360 pilot opportunity", pm.customer_followups)


if __name__ == "__main__":
    unittest.main()
