import os
import unittest

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_enterprise_platform.db")
os.environ.setdefault("PARDHA_OLLAMA_ENABLED", "false")
os.environ.setdefault("PARDHA_ADMIN_EMAIL", "founder@pardha.local")
os.environ.setdefault("PARDHA_ADMIN_PASSWORD", "test-admin-password")

from fastapi.testclient import TestClient

from app.db import SessionLocal, init_db
from app.db.models import AuditLog, BillingSubscription, Business, Tenant, TenantUser
from app.enterprise.service import has_permission
from app.main import app


class EnterprisePlatformTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        cls.client = TestClient(app)
        cls.client.get("/enterprise/tenants")

    def test_multi_tenant_rbac_billing_and_isolation_foundation(self):
        tenant = self.client.post("/enterprise/tenants", json={"name": "DP360 Customer", "slug": "dp360-customer", "plan": "professional"})
        self.assertEqual(tenant.status_code, 200)
        tenant_id = tenant.json()["tenant_id"]

        tenants = self.client.get("/enterprise/tenants")
        self.assertEqual(tenants.status_code, 200)
        self.assertTrue(any(item["tenant_id"] == tenant_id for item in tenants.json()))

        rbac = self.client.get("/enterprise/rbac")
        self.assertEqual(rbac.status_code, 200)
        self.assertIn("founder", rbac.json()["roles"])
        self.assertIn("viewer", rbac.json()["roles"])
        self.assertTrue(has_permission("founder", "write:billing"))
        self.assertTrue(has_permission("viewer", "read:business"))
        self.assertFalse(has_permission("viewer", "write:billing"))

        billing = self.client.get(f"/enterprise/billing?tenant_id={tenant_id}")
        self.assertEqual(billing.status_code, 200)
        self.assertEqual(billing.json()[0]["plan"], "professional")
        self.assertIn("users", billing.json()[0]["limits"])

        with SessionLocal() as session:
            self.assertIsNotNone(session.get(Tenant, tenant_id))
            self.assertGreaterEqual(session.query(BillingSubscription).count(), 1)
            default_tenant_id = session.query(Tenant).filter(Tenant.slug == "pardha-internal").one().tenant_id
            self.assertTrue(all(row.tenant_id == default_tenant_id for row in session.query(Business).filter(Business.business_name.in_(["UVA", "DP360", "EatOnTime", "Trevia EV"])).all()))
            self.assertGreaterEqual(session.query(TenantUser).count(), 1)

    def test_audit_observability_security_integrations_deployment_flags_and_governance(self):
        tenant_id = self.client.get("/enterprise/tenants").json()[0]["tenant_id"]
        audit = self.client.post(
            "/enterprise/audit",
            json={"tenant_id": tenant_id, "action": "approval.reviewed", "resource_type": "approval", "outcome": "success"},
        )
        self.assertEqual(audit.status_code, 200)

        logs = self.client.get(f"/enterprise/audit?tenant_id={tenant_id}")
        self.assertEqual(logs.status_code, 200)
        self.assertTrue(any(item["action"] == "approval.reviewed" for item in logs.json()))

        observability = self.client.get(f"/enterprise/observability?tenant_id={tenant_id}")
        self.assertEqual(observability.status_code, 200)
        self.assertIn("execution_metrics", observability.json())
        self.assertIn("api_metrics", observability.json())

        security = self.client.get("/enterprise/security")
        self.assertEqual(security.status_code, 200)
        self.assertEqual(security.json()["jwt_authentication"], "hs256_ready")
        self.assertTrue(security.json()["mfa_ready"])

        integrations = self.client.get(f"/enterprise/integrations?tenant_id={tenant_id}")
        self.assertEqual(integrations.status_code, 200)
        self.assertEqual({item["provider"] for item in integrations.json()}, {"google", "microsoft", "atlassian", "github", "slack", "teams"})
        self.assertTrue(all(item["configuration"]["secrets_management"] == "secret_reference_only" for item in integrations.json()))

        deployment = self.client.get("/enterprise/deployment/profiles")
        self.assertEqual(deployment.status_code, 200)
        self.assertEqual({item["environment"] for item in deployment.json()}, {"development", "testing", "staging", "production"})
        self.assertTrue(all(item["docker_ready"] and item["kubernetes_ready"] for item in deployment.json()))

        flag = self.client.post("/enterprise/feature-flags", json={"key": "tenant_beta_console", "name": "Tenant Beta Console", "enabled": True, "tenant_id": tenant_id, "rollout_percentage": 25})
        self.assertEqual(flag.status_code, 200)
        self.assertEqual(flag.json()["rollout_percentage"], 25)

        governance = self.client.get(f"/enterprise/governance?tenant_id={tenant_id}")
        self.assertEqual(governance.status_code, 200)
        self.assertTrue(governance.json()[0]["provider_switch_ready"])

        with SessionLocal() as session:
            self.assertGreaterEqual(session.query(AuditLog).count(), 1)

    def test_admin_dashboard_validation_and_auth_tokens(self):
        login = self.client.post("/auth/login", json={"email": "founder@pardha.local", "password": "test-admin-password"})
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()["jwt_token"].count(".") == 2)
        self.assertTrue(login.json()["refresh_token"])

        admin = self.client.get("/enterprise/admin")
        self.assertEqual(admin.status_code, 200)
        self.assertTrue(admin.json()["tenants"])
        self.assertIn("system_health", admin.json())
        self.assertIn("feature_flags", admin.json())

        dashboard = self.client.get("/enterprise/dashboard")
        self.assertEqual(dashboard.status_code, 200)
        self.assertTrue(dashboard.json()["businesses"]["isolated"])

        validation = self.client.get("/enterprise/validation")
        self.assertEqual(validation.status_code, 200)
        self.assertGreaterEqual(validation.json()["scenarios_run"], 200)
        self.assertGreaterEqual(validation.json()["score"], 98)


if __name__ == "__main__":
    unittest.main()
