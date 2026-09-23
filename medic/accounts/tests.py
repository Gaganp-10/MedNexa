import datetime
from django.test import TestCase
from django.core.cache import cache
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from accounts.models import User, DoctorProfile, PatientProfile
from accounts.access import get_accessible_patient
from django.http import Http404


class AccountsSecurityAndAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Doctor 1 & Doctor 2
        self.doc1 = User.objects.create_user(
            username="test_doc1", password="password123", role="doctor"
        )
        self.doc2 = User.objects.create_user(
            username="test_doc2", password="password123", role="doctor"
        )

        # Patient 1 (assigned to doc1)
        self.patient1_user = User.objects.create_user(
            username="test_patient1", password="password123", role="patient"
        )
        self.patient1_profile = PatientProfile.objects.create(
            user=self.patient1_user,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc1
        )

        # Patient 2 (assigned to doc2)
        self.patient2_user = User.objects.create_user(
            username="test_patient2", password="password123", role="patient"
        )
        self.patient2_profile = PatientProfile.objects.create(
            user=self.patient2_user,
            surgery_type="Knee Surgery",
            surgery_date=datetime.date(2026, 3, 5),
            doctor=self.doc2
        )

    def test_anonymous_access_denied_401(self):
        """Anonymous callers must receive 401 Unauthorized across protected endpoints."""
        endpoints = [
            "/api/doctor/overview/",
            "/api/doctor/patients/",
            f"/api/patient/{self.patient1_profile.id}/logs/",
            f"/api/patient/{self.patient1_profile.id}/wounds/",
            f"/api/patient/{self.patient1_profile.id}/alerts/",
            f"/api/patient/{self.patient1_profile.id}/recovery-trend/",
            f"/api/patient/{self.patient1_profile.id}/risk/",
        ]
        for url in endpoints:
            response = self.client.get(url)
            self.assertEqual(
                response.status_code,
                status.HTTP_401_UNAUTHORIZED,
                f"Expected 401 for anonymous access to {url}, got {response.status_code}"
            )

    def test_central_access_helper_boundaries(self):
        """Test get_accessible_patient allows self & assigned doctor, raises 404 for others."""
        # Patient 1 accessing self -> OK
        self.assertEqual(
            get_accessible_patient(self.patient1_user, self.patient1_profile.id),
            self.patient1_profile
        )
        # Doctor 1 accessing assigned patient 1 -> OK
        self.assertEqual(
            get_accessible_patient(self.doc1, self.patient1_profile.id),
            self.patient1_profile
        )
        # Doctor 2 accessing unassigned patient 1 -> Http404
        with self.assertRaises(Http404):
            get_accessible_patient(self.doc2, self.patient1_profile.id)

        # Patient 2 accessing Patient 1 -> Http404
        with self.assertRaises(Http404):
            get_accessible_patient(self.patient2_user, self.patient1_profile.id)

    def test_doctor_access_to_assigned_vs_unassigned_endpoints(self):
        """Assigned doctor gets 200; unassigned doctor gets 404."""
        self.client.force_authenticate(user=self.doc1)

        # Doc1 accessing assigned patient 1 -> 200
        res_assigned = self.client.get(f"/api/patient/{self.patient1_profile.id}/logs/")
        self.assertEqual(res_assigned.status_code, status.HTTP_200_OK)

        res_risk = self.client.get(f"/api/patient/{self.patient1_profile.id}/risk/")
        self.assertEqual(res_risk.status_code, status.HTTP_200_OK)

        # Doc1 accessing unassigned patient 2 -> 404
        res_unassigned = self.client.get(f"/api/patient/{self.patient2_profile.id}/logs/")
        self.assertEqual(res_unassigned.status_code, status.HTTP_404_NOT_FOUND)

        res_unassigned_risk = self.client.get(f"/api/patient/{self.patient2_profile.id}/risk/")
        self.assertEqual(res_unassigned_risk.status_code, status.HTTP_404_NOT_FOUND)

    def test_patient_cannot_access_other_patient_data(self):
        """Patient 1 cannot view Patient 2's alerts or recovery trend (must get 404)."""
        self.client.force_authenticate(user=self.patient1_user)

        res_alerts = self.client.get(f"/api/patient/{self.patient2_profile.id}/alerts/")
        self.assertEqual(res_alerts.status_code, status.HTTP_404_NOT_FOUND)

        res_trend = self.client.get(f"/api/patient/{self.patient2_profile.id}/recovery-trend/")
        self.assertEqual(res_trend.status_code, status.HTTP_404_NOT_FOUND)

    def test_doctor_overview_endpoint(self):
        """Doctor overview returns assigned patients and handles empty log states safely."""
        self.client.force_authenticate(user=self.doc1)

        response = self.client.get("/api/doctor/overview/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data
        self.assertEqual(data["total_patients"], 1)
        self.assertEqual(data["patients"][0]["patient_id"], self.patient1_profile.id)
        self.assertEqual(data["patients"][0]["latest_recovery_score"], 100)
        self.assertIn("Insufficient data", data["patients"][0]["latest_risk_indicator"])

    def test_patient_cannot_access_doctor_endpoints(self):
        """Patient role must be forbidden (403) from doctor endpoints."""
        self.client.force_authenticate(user=self.patient1_user)

        res_overview = self.client.get("/api/doctor/overview/")
        self.assertEqual(res_overview.status_code, status.HTTP_403_FORBIDDEN)

        res_patients = self.client.get("/api/doctor/patients/")
        self.assertEqual(res_patients.status_code, status.HTTP_403_FORBIDDEN)

    def test_auth_me_for_doctor(self):
        """GET /api/auth/me/ returns doctor identity and doctor_profile_id."""
        doc_profile = DoctorProfile.objects.create(user=self.doc1, specialization="Surgeon")
        self.client.force_authenticate(user=self.doc1)

        res = self.client.get("/api/auth/me/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.doc1.id)
        self.assertEqual(res.data["username"], self.doc1.username)
        self.assertEqual(res.data["role"], "doctor")
        self.assertEqual(res.data["doctor_profile_id"], doc_profile.id)

    def test_auth_me_for_patient_with_assigned_doctor(self):
        """GET /api/auth/me/ returns patient profile and assigned doctor details."""
        self.client.force_authenticate(user=self.patient1_user)

        res = self.client.get("/api/auth/me/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.patient1_user.id)
        self.assertEqual(res.data["username"], self.patient1_user.username)
        self.assertEqual(res.data["role"], "patient")
        self.assertEqual(res.data["patient_profile_id"], self.patient1_profile.id)
        self.assertEqual(res.data["assigned_doctor"]["id"], self.doc1.id)
        self.assertEqual(res.data["assigned_doctor"]["name"], self.doc1.get_full_name() or self.doc1.username)

    def test_auth_me_for_patient_without_assigned_doctor(self):
        """GET /api/auth/me/ handles patients without assigned doctor gracefully."""
        p_unassigned = User.objects.create_user(username="p_no_doc", password="password123", role="patient")
        p_profile = PatientProfile.objects.create(
            user=p_unassigned, surgery_type="Test", surgery_date=datetime.date(2026, 1, 1), doctor=None
        )
        self.client.force_authenticate(user=p_unassigned)

        res = self.client.get("/api/auth/me/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["patient_profile_id"], p_profile.id)
        self.assertIsNone(res.data["assigned_doctor"])

    def test_patient_profile_me_endpoint(self):
        """GET /api/patient/profile/ returns patient profile for patient and 403 for doctor."""
        self.client.force_authenticate(user=self.patient1_user)
        res_patient = self.client.get("/api/patient/profile/")
        self.assertEqual(res_patient.status_code, status.HTTP_200_OK)
        self.assertEqual(res_patient.data["patient_profile_id"], self.patient1_profile.id)

        self.client.force_authenticate(user=self.doc1)
        res_doc = self.client.get("/api/patient/profile/")
        self.assertEqual(res_doc.status_code, status.HTTP_403_FORBIDDEN)

    def test_seed_demo_refuses_when_debug_false(self):
        """seed_demo must refuse to execute when DEBUG is False."""
        from django.core.management import call_command
        from django.core.management.base import CommandError
        from django.test import override_settings

        with override_settings(DEBUG=False):
            with self.assertRaises(CommandError) as cm:
                call_command("seed_demo")
            self.assertIn("DEBUG is True", str(cm.exception))


class LoginAndCredentialTests(TestCase):
    """
    Phase 7 gap: tests for /api/token/ (login) endpoint —
    both roles succeeding and invalid credentials being rejected.
    """

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.doc = User.objects.create_user(
            username="login_doc", password="correctpass", role="doctor"
        )
        self.patient = User.objects.create_user(
            username="login_patient", password="correctpass", role="patient"
        )
        PatientProfile.objects.create(
            user=self.patient,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
        )

    def tearDown(self):
        cache.clear()

    def test_doctor_login_returns_token_pair(self):
        """Successful doctor login returns access and refresh JWT tokens."""
        res = self.client.post(
            "/api/token/",
            {"username": "login_doc", "password": "correctpass"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)
        self.assertTrue(len(res.data["access"]) > 20)
        self.assertTrue(len(res.data["refresh"]) > 20)

    def test_patient_login_returns_token_pair(self):
        """Successful patient login returns access and refresh JWT tokens."""
        res = self.client.post(
            "/api/token/",
            {"username": "login_patient", "password": "correctpass"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_wrong_password_returns_401(self):
        """Incorrect password must be rejected with 401 Unauthorized."""
        res = self.client.post(
            "/api/token/",
            {"username": "login_doc", "password": "WRONG_PASSWORD"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", res.data)

    def test_nonexistent_user_returns_401(self):
        """Login with a username that does not exist must return 401."""
        res = self.client.post(
            "/api/token/",
            {"username": "ghost_user_99999", "password": "any"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_password_field_returns_400(self):
        """Login request with missing password field returns 400 Bad Request."""
        res = self.client.post(
            "/api/token/",
            {"username": "login_doc"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_username_field_returns_400(self):
        """Login request with missing username field returns 400 Bad Request."""
        res = self.client.post(
            "/api/token/",
            {"password": "correctpass"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_can_be_used_to_access_protected_endpoint(self):
        """A valid access token returned by /api/token/ actually grants API access."""
        login_res = self.client.post(
            "/api/token/",
            {"username": "login_doc", "password": "correctpass"},
            format="json"
        )
        access_token = login_res.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        me_res = self.client.get("/api/auth/me/")
        self.assertEqual(me_res.status_code, status.HTTP_200_OK)
        self.assertEqual(me_res.data["username"], "login_doc")

    def test_refresh_token_produces_new_access_token(self):
        """A valid refresh token can obtain a new access token."""
        login_res = self.client.post(
            "/api/token/",
            {"username": "login_doc", "password": "correctpass"},
            format="json"
        )
        refresh_token = login_res.data["refresh"]
        refresh_res = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh_token},
            format="json"
        )
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_res.data)

    def test_login_rate_limiting_enforces_429(self):
        """Phase 8: After 5 attempts within a minute, 6th attempt is throttled with 429."""
        cache.clear()
        for _ in range(5):
            self.client.post(
                "/api/token/",
                {"username": "login_doc", "password": "wrong_password"},
                format="json"
            )
        res = self.client.post(
            "/api/token/",
            {"username": "login_doc", "password": "wrong_password"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_429_TOO_MANY_REQUESTS)



class UnassignedDoctorAllEndpointsTests(TestCase):
    """
    Phase 7 gap: systematic check that an unassigned doctor gets 404
    on every patient-scoped endpoint, not just logs/risk.
    """

    def setUp(self):
        self.client = APIClient()

        self.doc1 = User.objects.create_user(
            username="unassigned_doc1", password="pass", role="doctor"
        )
        self.doc2 = User.objects.create_user(
            username="unassigned_doc2", password="pass", role="doctor"
        )
        self.p1_user = User.objects.create_user(
            username="unassigned_p1", password="pass", role="patient"
        )
        self.p1_profile = PatientProfile.objects.create(
            user=self.p1_user,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc1
        )

    def test_unassigned_doctor_all_patient_endpoints_return_404(self):
        """
        Doctor 2 (not assigned to patient 1) must receive 404 on all
        patient-scoped endpoints that use get_accessible_patient.
        """
        self.client.force_authenticate(user=self.doc2)
        pid = self.p1_profile.id
        endpoints = [
            f"/api/patient/{pid}/logs/",
            f"/api/patient/{pid}/wounds/",
            f"/api/patient/{pid}/alerts/",
            f"/api/patient/{pid}/recovery-trend/",
            f"/api/patient/{pid}/risk/",
            f"/api/patient/{pid}/medication-adherence/",
            f"/api/medication/{pid}/",
        ]
        for url in endpoints:
            res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                status.HTTP_404_NOT_FOUND,
                f"Expected 404 for unassigned doctor at {url}, got {res.status_code}"
            )


class CrossPatientIsolationAllEndpointsTests(TestCase):
    """
    Phase 7 gap: patient cannot access another patient's data on any endpoint.
    """

    def setUp(self):
        self.client = APIClient()

        self.doc1 = User.objects.create_user(
            username="cross_doc1", password="pass", role="doctor"
        )
        self.doc2 = User.objects.create_user(
            username="cross_doc2", password="pass", role="doctor"
        )
        self.p1_user = User.objects.create_user(
            username="cross_p1", password="pass", role="patient"
        )
        self.p1_profile = PatientProfile.objects.create(
            user=self.p1_user,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc1
        )
        self.p2_user = User.objects.create_user(
            username="cross_p2", password="pass", role="patient"
        )
        self.p2_profile = PatientProfile.objects.create(
            user=self.p2_user,
            surgery_type="Knee Surgery",
            surgery_date=datetime.date(2026, 3, 5),
            doctor=self.doc2
        )

    def test_patient_cannot_access_other_patient_all_endpoints(self):
        """
        Patient 2 must receive 404 on every endpoint scoped to Patient 1.
        """
        self.client.force_authenticate(user=self.p2_user)
        pid = self.p1_profile.id
        endpoints = [
            f"/api/patient/{pid}/logs/",
            f"/api/patient/{pid}/wounds/",
            f"/api/patient/{pid}/alerts/",
            f"/api/patient/{pid}/recovery-trend/",
            f"/api/patient/{pid}/risk/",
            f"/api/patient/{pid}/medication-adherence/",
            f"/api/medication/{pid}/",
        ]
        for url in endpoints:
            res = self.client.get(url)
            self.assertEqual(
                res.status_code,
                status.HTTP_404_NOT_FOUND,
                f"Expected 404 for cross-patient access to {url}, got {res.status_code}"
            )
