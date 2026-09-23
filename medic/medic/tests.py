"""
Smoke tests for Phase 6: API documentation (drf-spectacular).
Verifies that /api/schema/ and /api/docs/ respond correctly.
"""
from django.test import TestCase, Client
from rest_framework.test import APIClient
from accounts.models import User


class ApiDocSmokeTests(TestCase):
    """
    Smoke tests ensuring the schema and Swagger UI endpoints are accessible.
    No behavior changes from earlier phases should be broken.
    """

    def setUp(self):
        self.client = APIClient()
        self.plain_client = Client()

    def test_schema_endpoint_returns_200_unauthenticated(self):
        """
        GET /api/schema/ should return 200 OK without authentication,
        because SERVE_PERMISSIONS = AllowAny in dev settings.
        """
        response = self.plain_client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        # Should be YAML or JSON OpenAPI content
        content_type = response.get("Content-Type", "")
        self.assertTrue(
            "yaml" in content_type or "json" in content_type or "application" in content_type,
            f"Unexpected Content-Type: {content_type}"
        )

    def test_docs_endpoint_returns_200_unauthenticated(self):
        """
        GET /api/docs/ should return 200 OK with Swagger UI HTML
        without authentication in development mode.
        """
        response = self.plain_client.get("/api/docs/")
        self.assertEqual(response.status_code, 200)
        content_type = response.get("Content-Type", "")
        self.assertIn("text/html", content_type)

    def test_schema_contains_api_title(self):
        """Schema YAML/JSON response should include the configured API title."""
        response = self.plain_client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("MEDIC API", content)

    def test_schema_contains_medical_safety_notice(self):
        """Schema description should contain the medical safety disclaimer."""
        response = self.plain_client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("MEDICAL SAFETY NOTICE", content)

    def test_schema_contains_authentication_section(self):
        """Schema should include jwtAuth security scheme."""
        response = self.plain_client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        self.assertIn("jwtAuth", content)

    def test_schema_endpoint_authenticated_also_returns_200(self):
        """Authenticated users can also fetch the schema."""
        user = User.objects.create_user(
            username="schema_test_user", password="testpass123", role="doctor"
        )
        self.client.force_authenticate(user=user)
        response = self.client.get("/api/schema/")
        self.assertEqual(response.status_code, 200)


class HealthEndpointSmokeTest(TestCase):
    """
    Phase 7 gap: test the public system health check endpoint.
    """

    def setUp(self):
        self.plain_client = Client()

    def test_health_endpoint_returns_200(self):
        """GET /health/ must return 200 OK without authentication."""
        response = self.plain_client.get("/health/")
        self.assertEqual(response.status_code, 200)

    def test_health_endpoint_returns_running_status(self):
        """GET /health/ response must contain status=running and service name."""
        response = self.plain_client.get("/health/")
        self.assertEqual(response.status_code, 200)
        import json
        data = json.loads(response.content)
        self.assertEqual(data["status"], "running")
        self.assertIn("medic", data["service"].lower())
        self.assertIn("version", data)
