import datetime
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import User, PatientProfile
from medication.models import Medication


class MedicationSecurityAndAuthorizationTests(TestCase):
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
        self.p1_user = User.objects.create_user(
            username="test_p1", password="password123", role="patient"
        )
        self.p1_profile = PatientProfile.objects.create(
            user=self.p1_user,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc1
        )

        # Patient 2 (assigned to doc2)
        self.p2_user = User.objects.create_user(
            username="test_p2", password="password123", role="patient"
        )
        self.p2_profile = PatientProfile.objects.create(
            user=self.p2_user,
            surgery_type="Knee Surgery",
            surgery_date=datetime.date(2026, 3, 2),
            doctor=self.doc2
        )

        # Pre-existing medication for Patient 1
        self.med1 = Medication.objects.create(
            patient=self.p1_profile,
            medicine_name="Amoxicillin",
            dosage="500mg",
            time=datetime.time(8, 0),
            taken_status=False
        )

    def test_anonymous_access_denied_401(self):
        """Anonymous callers must receive 401 Unauthorized."""
        endpoints = [
            "/api/medication/create/",
            f"/api/medication/{self.p1_profile.id}/",
            f"/api/medication/{self.med1.id}/update/",
        ]
        for url in endpoints:
            res = self.client.get(url) if "update" not in url else self.client.patch(url, {"taken_status": True})
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_doctor_can_prescribe_for_assigned_patient(self):
        """Assigned doctor can create prescriptions for their patients."""
        self.client.force_authenticate(user=self.doc1)

        payload = {
            "patient_id": self.p1_profile.id,
            "medicine_name": "Paracetamol",
            "dosage": "500mg",
            "time": "12:00:00",
        }
        res = self.client.post("/api/medication/create/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Medication.objects.filter(medicine_name="Paracetamol", patient=self.p1_profile).exists())

    def test_doctor_cannot_prescribe_for_unassigned_patient(self):
        """Doctor cannot create prescriptions for patients not assigned to them (must return 404)."""
        self.client.force_authenticate(user=self.doc1)

        payload = {
            "patient_id": self.p2_profile.id,  # Assigned to doc2, NOT doc1
            "medicine_name": "Ibuprofen",
            "dosage": "400mg",
            "time": "14:00:00",
        }
        res = self.client.post("/api/medication/create/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_patient_cannot_create_medication(self):
        """Patients are not allowed to create prescriptions (must return 403)."""
        self.client.force_authenticate(user=self.p1_user)

        payload = {
            "patient_id": self.p1_profile.id,
            "medicine_name": "Aspirin",
            "dosage": "100mg",
            "time": "09:00:00",
        }
        res = self.client.post("/api/medication/create/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_can_mark_own_medication_as_taken(self):
        """Patients can update the taken_status of their own medication doses via PATCH."""
        self.client.force_authenticate(user=self.p1_user)

        self.assertFalse(self.med1.taken_status)
        res = self.client.patch(
            f"/api/medication/{self.med1.id}/update/",
            {"taken_status": True},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.med1.refresh_from_db()
        self.assertTrue(self.med1.taken_status)

    def test_patient_cannot_mark_other_patient_medication(self):
        """Patient 2 cannot mark Patient 1's medication as taken (must return 404)."""
        self.client.force_authenticate(user=self.p2_user)

        res = self.client.patch(
            f"/api/medication/{self.med1.id}/update/",
            {"taken_status": True},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_medication_list_scoped_by_access_helper(self):
        """Medication list is accessible only to self and assigned doctor."""
        list_url = f"/api/medication/{self.p1_profile.id}/"

        # Assigned patient -> 200
        self.client.force_authenticate(user=self.p1_user)
        res_self = self.client.get(list_url)
        self.assertEqual(res_self.status_code, status.HTTP_200_OK)

        # Assigned doctor -> 200
        self.client.force_authenticate(user=self.doc1)
        res_doc1 = self.client.get(list_url)
        self.assertEqual(res_doc1.status_code, status.HTTP_200_OK)

        # Unassigned doctor -> 404
        self.client.force_authenticate(user=self.doc2)
        res_doc2 = self.client.get(list_url)
        self.assertEqual(res_doc2.status_code, status.HTTP_404_NOT_FOUND)

        # Other patient -> 404
        self.client.force_authenticate(user=self.p2_user)
        res_p2 = self.client.get(list_url)
        self.assertEqual(res_p2.status_code, status.HTTP_404_NOT_FOUND)
