"""PE0OM-75 (PE0OM-56 1/5): test-database guard, external-write kill switch, Jira dry-run default.

Network boundaries (httpx.Client, urlopen) are replaced with mocks in these tests. The mocks
only prove whether a request *would have been sent*; nothing here is live integration evidence.
Dummy endpoints use the reserved ".invalid" domain so they can never resolve.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.db import init_db
from app.db.safety import UnsafeTestDatabaseError, assert_safe_test_database
from app.hubspot.client import HubSpotClient, HubSpotClientError
from app.jira.client import JiraClient
from app.jira.schemas import JiraSyncRequest
from app.main import app
from app.security.write_guard import EXTERNAL_WRITES_ENV, KILL_SWITCH, NO_VERIFIED_AUTHORIZATION, ExternalWriteBlocked

PARDHA_CORE = Path(__file__).resolve().parents[1]
DUMMY_JIRA_ENV = {
    "JIRA_URL": "https://jira.invalid",
    "JIRA_EMAIL": "qa@example.invalid",
    "JIRA_API_TOKEN": "dummy-not-a-real-token",
    "JIRA_PROJECT_KEY": "QA",
    "PARDHA_JIRA_ENABLED": "true",
}


def _without(*names: str) -> dict:
    return {key: value for key, value in os.environ.items() if key not in names}


class TestDatabaseGuardTestCase(unittest.TestCase):
    def test_rejects_unset_developer_server_and_persistent_databases(self):
        for url in (
            None,
            "",
            "not a url",
            # Developer and other server databases: never provably disposable, whatever the name.
            "postgresql+psycopg2:///pardha_core",
            "postgresql+psycopg2://user@db.internal/pardha_core",
            "postgresql+psycopg2://user@localhost/pardha_test",
            "postgresql+psycopg2://user@localhost/test_pardha",
            "mysql://user@localhost/pardha_test",
            # Persistent SQLite files outside a temporary directory, including "test"-named ones.
            "sqlite:////srv/pardha/pardha_dev.db",
            "sqlite:///./test_feature.db",
            "sqlite:///./pardha_test.db",
        ):
            with self.subTest(url=url):
                with self.assertRaises(UnsafeTestDatabaseError):
                    assert_safe_test_database(url)

    def test_rejects_existing_sqlite_file_even_in_temp_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            existing = Path(directory) / "reused.db"
            existing.write_bytes(b"")
            with self.assertRaises(UnsafeTestDatabaseError):
                assert_safe_test_database(f"sqlite:///{existing}")

    def test_accepts_only_fresh_temporary_or_in_memory_databases(self):
        with tempfile.TemporaryDirectory() as directory:
            for url in ("sqlite://", "sqlite:///:memory:", f"sqlite:///{Path(directory) / 'fresh.db'}"):
                with self.subTest(url=url):
                    assert_safe_test_database(url)

    def _import_app_db(self, env: dict) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, "-c", "import app.db"],
            cwd=PARDHA_CORE,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def test_test_run_fails_fast_before_engine_when_database_url_is_unset(self):
        result = self._import_app_db({**_without("DATABASE_URL"), "PARDHA_TESTING": "1"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing to run tests", result.stderr)

    def test_test_run_fails_fast_for_developer_database(self):
        result = self._import_app_db({**_without("DATABASE_URL"), "PARDHA_TESTING": "1", "DATABASE_URL": "postgresql+psycopg2:///pardha_core"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing to run tests", result.stderr)

    def test_test_run_fails_fast_for_persistent_sqlite_file(self):
        result = self._import_app_db({**_without("DATABASE_URL"), "PARDHA_TESTING": "1", "DATABASE_URL": "sqlite:///./test_persistent.db"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Refusing to run tests", result.stderr)

    def test_test_run_starts_with_fresh_disposable_database(self):
        with tempfile.TemporaryDirectory() as directory:
            url = f"sqlite:///{Path(directory) / 'fresh.db'}"
            result = self._import_app_db({**_without("DATABASE_URL"), "PARDHA_TESTING": "1", "DATABASE_URL": url})
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_guard_is_inert_outside_test_runs(self):
        result = self._import_app_db(_without("DATABASE_URL", "PARDHA_TESTING"))
        self.assertEqual(result.returncode, 0, result.stderr)


class ExternalWriteKillSwitchTestCase(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        os.environ.pop(EXTERNAL_WRITES_ENV, None)

    def tearDown(self):
        self.env.stop()

    def _jira(self) -> JiraClient:
        return JiraClient(jira_url="https://jira.invalid", email="qa@example.invalid", api_token="dummy", project_key="QA")

    def test_jira_writes_are_blocked_by_default_without_network(self):
        with patch("app.jira.client.httpx.Client") as http_client:
            for call in (
                lambda client: client.create_epic("Epic"),
                lambda client: client.create_story("Story"),
                lambda client: client.update_issue("QA-1", {"summary": "x"}),
                lambda client: client._request("DELETE", "/rest/api/3/issue/QA-1"),
            ):
                with self.assertRaises(ExternalWriteBlocked) as raised:
                    call(self._jira())
                self.assertEqual(raised.exception.reason, KILL_SWITCH)
            http_client.assert_not_called()

    def test_jira_reads_are_not_blocked(self):
        with patch("app.jira.client.httpx.Client") as http_client:
            response = MagicMock(content=b'{"key": "QA-1"}')
            response.json.return_value = {"key": "QA-1"}
            http_client.return_value.__enter__.return_value.request.return_value = response
            self.assertEqual(self._jira().get_issue("QA-1"), {"key": "QA-1"})
            http_client.assert_called_once()

    def test_enabling_kill_switch_alone_never_sends_a_jira_write(self):
        os.environ[EXTERNAL_WRITES_ENV] = "true"
        with patch("app.jira.client.httpx.Client") as http_client:
            for call in (
                lambda client: client.create_epic("Epic"),
                lambda client: client.update_issue("QA-1", {"summary": "x"}),
                lambda client: client._request("DELETE", "/rest/api/3/issue/QA-1"),
            ):
                with self.assertRaises(ExternalWriteBlocked) as raised:
                    call(self._jira())
                self.assertEqual(raised.exception.reason, NO_VERIFIED_AUTHORIZATION)
            write_calls = [c for c in http_client.return_value.__enter__.return_value.request.call_args_list if c.args and c.args[0] != "GET"]
            self.assertEqual(write_calls, [])

    def test_enabling_kill_switch_alone_never_sends_a_hubspot_write(self):
        os.environ[EXTERNAL_WRITES_ENV] = "true"
        with patch("app.hubspot.client.urlopen") as urlopen:
            with self.assertRaises(HubSpotClientError) as raised:
                HubSpotClient("dummy", base_url="https://hubspot.invalid").create_deal({"dealname": "x"})
            self.assertFalse(raised.exception.retryable)
            self.assertEqual(raised.exception.__cause__.reason, NO_VERIFIED_AUTHORIZATION)
            urlopen.assert_not_called()

    def test_hubspot_writes_are_blocked_as_non_retryable_without_network(self):
        with patch("app.hubspot.client.urlopen") as urlopen:
            with self.assertRaises(HubSpotClientError) as raised:
                HubSpotClient("dummy", base_url="https://hubspot.invalid").create_contact({"email": "a@example.invalid"})
            self.assertFalse(raised.exception.retryable)
            self.assertIsInstance(raised.exception.__cause__, ExternalWriteBlocked)
            urlopen.assert_not_called()

    def test_blocked_transition_makes_zero_network_calls_with_switch_off_or_on(self):
        # Adversarial: the transition path used to list transitions (GET) before the write guard ran.
        # Every network layer is replaced; any connection attempt fails the test.
        from app.jira.service import update_engineering_task_status

        def no_network(*_args, **_kwargs):
            raise AssertionError("network access attempted by a blocked Jira transition")

        for switch, expected in ((None, KILL_SWITCH), ("true", NO_VERIFIED_AUTHORIZATION)):
            if switch is None:
                os.environ.pop(EXTERNAL_WRITES_ENV, None)
            else:
                os.environ[EXTERNAL_WRITES_ENV] = switch
            for call in (
                lambda: self._jira().transition_issue("QA-1", "Done"),
                lambda: update_engineering_task_status("QA-1", "Done", client=self._jira()),
            ):
                with self.subTest(switch=switch), patch("app.jira.client.httpx.Client") as http_client, patch("socket.socket.connect", no_network), patch("socket.create_connection", no_network):
                    with self.assertRaises(ExternalWriteBlocked) as raised:
                        call()
                    self.assertEqual(raised.exception.reason, expected)
                    http_client.assert_not_called()

    def test_unrecognised_values_do_not_enable_writes(self):
        for value in ("", "0", "false", "no", "maybe", "TRUEISH"):
            os.environ[EXTERNAL_WRITES_ENV] = value
            with self.subTest(value=value), patch("app.jira.client.httpx.Client") as http_client:
                with self.assertRaises(ExternalWriteBlocked):
                    self._jira().create_epic("Epic")
                http_client.assert_not_called()


class JiraSyncDryRunDefaultTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)

    def setUp(self):
        self.env = patch.dict(os.environ, DUMMY_JIRA_ENV, clear=False)
        self.env.start()
        os.environ.pop(EXTERNAL_WRITES_ENV, None)

    def tearDown(self):
        self.env.stop()

    def _payload(self, **extra) -> dict:
        return {"title": "Dry run objective", "description": "No external write expected.", "business_name": "DP360", "priority": "medium", **extra}

    def test_schema_defaults_to_dry_run(self):
        self.assertTrue(JiraSyncRequest().dry_run)

    def test_sync_without_dry_run_flag_sends_nothing_to_jira(self):
        with patch("app.jira.client.httpx.Client") as http_client:
            response = self.client.post("/jira/sync", json=self._payload())
        self.assertEqual(response.status_code, 201, response.text)
        http_client.assert_not_called()

    def test_explicit_live_sync_is_blocked_while_writes_are_disabled(self):
        with patch("app.jira.client.httpx.Client") as http_client:
            response = self.client.post("/jira/sync", json=self._payload(dry_run=False))
        self.assertEqual(response.status_code, 403)
        self.assertIn("External write blocked", response.json()["detail"])
        http_client.assert_not_called()

    def test_explicit_live_sync_is_blocked_even_with_kill_switch_enabled(self):
        os.environ[EXTERNAL_WRITES_ENV] = "true"
        with patch("app.jira.client.httpx.Client") as http_client:
            response = self.client.post("/jira/sync", json=self._payload(dry_run=False))
        self.assertEqual(response.status_code, 403)
        self.assertIn("no verified exact-payload founder approval", response.json()["detail"])
        http_client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
