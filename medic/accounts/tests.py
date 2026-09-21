import datetime
from django.test import TestCase
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
