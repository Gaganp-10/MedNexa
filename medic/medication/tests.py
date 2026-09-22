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


class MedicationDoseAndReminderTests(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.doc1 = User.objects.create_user(
            username="dose_doc1", password="password123", role="doctor"
        )
        self.doc2 = User.objects.create_user(
            username="dose_doc2", password="password123", role="doctor"
        )

        self.p1_user = User.objects.create_user(
            username="dose_p1", password="password123", role="patient"
        )
        self.p1_profile = PatientProfile.objects.create(
            user=self.p1_user,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc1
        )

        self.p2_user = User.objects.create_user(
            username="dose_p2", password="password123", role="patient"
        )
        self.p2_profile = PatientProfile.objects.create(
            user=self.p2_user,
            surgery_type="Knee Surgery",
            surgery_date=datetime.date(2026, 3, 2),
            doctor=self.doc2
        )

        self.med1 = Medication.objects.create(
            patient=self.p1_profile,
            medicine_name="Amoxicillin",
            dosage="500mg",
            time=datetime.time(8, 0)
        )

        self.med2 = Medication.objects.create(
            patient=self.p2_profile,
            medicine_name="Ibuprofen",
            dosage="400mg",
            time=datetime.time(12, 0)
        )

    def test_dose_generation_is_idempotent(self):
        """Generating doses multiple times never creates duplicates."""
        from medication.services import generate_upcoming_doses
        from medication.models import MedicationDose

        doses_first = generate_upcoming_doses(self.med1, days=7)
        self.assertEqual(len(doses_first), 7)
        self.assertEqual(MedicationDose.objects.filter(medication=self.med1).count(), 7)

        # Running a second time should return existing without adding duplicates
        doses_second = generate_upcoming_doses(self.med1, days=7)
        self.assertEqual(len(doses_second), 7)
        self.assertEqual(MedicationDose.objects.filter(medication=self.med1).count(), 7)

    def test_reminder_sent_exactly_once_inside_window(self):
        """Reminders fire inside 30m window and never duplicate."""
        from django.utils import timezone
        from medication.models import MedicationDose
        from medication.reminders import check_and_send_reminders

        now = timezone.now()

        # Dose 1: 15 minutes away (inside 30m window)
        dose_inside = MedicationDose.objects.create(
            medication=self.med1,
            scheduled_for=now + datetime.timedelta(minutes=15),
            status="pending"
        )

        # Dose 2: 45 minutes away (outside 30m window)
        dose_outside = MedicationDose.objects.create(
            medication=self.med1,
            scheduled_for=now + datetime.timedelta(minutes=45),
            status="pending"
        )

        # First run: should pick up dose_inside only
        sent = check_and_send_reminders(reference_time=now, window_minutes=30)
        self.assertEqual(sent, 1)

        dose_inside.refresh_from_db()
        dose_outside.refresh_from_db()
        self.assertIsNotNone(dose_inside.reminder_sent_at)
        self.assertIsNone(dose_outside.reminder_sent_at)

        # Second run immediately after: must NOT re-send reminder for dose_inside
        sent_again = check_and_send_reminders(reference_time=now, window_minutes=30)
        self.assertEqual(sent_again, 0)

    def test_dose_past_grace_period_becomes_missed_and_alerts_doctor(self):
        """Pending doses past 2-hour grace period become missed and generate doctor alert."""
        from django.utils import timezone
        from medication.models import MedicationDose
        from medication.reminders import check_and_mark_missed_doses
        from alerts.models import Alert

        now = timezone.now()
        overdue_dose = MedicationDose.objects.create(
            medication=self.med1,
            scheduled_for=now - datetime.timedelta(hours=3),
            status="pending"
        )

        missed_count = check_and_mark_missed_doses(reference_time=now, grace_period_hours=2)
        self.assertEqual(missed_count, 1)

        overdue_dose.refresh_from_db()
        self.assertEqual(overdue_dose.status, "missed")

        # Confirm doctor alert was generated
        self.assertTrue(
            Alert.objects.filter(patient=self.p1_profile, severity="low", message__contains="missed").exists()
        )

    def test_patient_can_take_own_dose(self):
        """Patient can mark their own dose as taken via PATCH."""
        from django.utils import timezone
        from medication.models import MedicationDose

        now = timezone.now()
        dose = MedicationDose.objects.create(
            medication=self.med1,
            scheduled_for=now,
            status="pending"
        )

        self.client.force_authenticate(user=self.p1_user)
        res = self.client.patch(f"/api/medication/doses/{dose.id}/take/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        dose.refresh_from_db()
        self.assertEqual(dose.status, "taken")
        self.assertIsNotNone(dose.taken_at)

    def test_patient_cannot_take_other_patient_dose_404(self):
        """Patient 2 cannot mark Patient 1's dose as taken (must return 404)."""
        from django.utils import timezone
        from medication.models import MedicationDose

        now = timezone.now()
        dose1 = MedicationDose.objects.create(
            medication=self.med1,
            scheduled_for=now,
            status="pending"
        )

        self.client.force_authenticate(user=self.p2_user)
        res = self.client.patch(f"/api/medication/doses/{dose1.id}/take/")
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_doctor_cannot_take_patient_dose_403(self):
        """Doctors are forbidden (403) from marking patient doses as taken."""
        from django.utils import timezone
        from medication.models import MedicationDose

        now = timezone.now()
        dose1 = MedicationDose.objects.create(
            medication=self.med1,
            scheduled_for=now,
            status="pending"
        )

        self.client.force_authenticate(user=self.doc1)
        res = self.client.patch(f"/api/medication/doses/{dose1.id}/take/")
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_adherence_summary_calculation_for_mixed_states(self):
        """Adherence calculation accurately reflects taken, missed, and pending proportions."""
        from django.utils import timezone
        from medication.models import MedicationDose
        from medication.services import calculate_patient_adherence

        now = timezone.now()
        # 2 taken, 1 missed, 1 pending scheduled in the past 7 days
        MedicationDose.objects.create(
            medication=self.med1, scheduled_for=now - datetime.timedelta(days=1), status="taken", taken_at=now
        )
        MedicationDose.objects.create(
            medication=self.med1, scheduled_for=now - datetime.timedelta(days=2), status="taken", taken_at=now
        )
        MedicationDose.objects.create(
            medication=self.med1, scheduled_for=now - datetime.timedelta(days=3), status="missed"
        )
        MedicationDose.objects.create(
            medication=self.med1, scheduled_for=now - datetime.timedelta(hours=1), status="pending"
        )

        adherence = calculate_patient_adherence(self.p1_profile, window_days=7, reference_time=now)
        self.assertEqual(adherence["total_due"], 4)
        self.assertEqual(adherence["taken"], 2)
        self.assertEqual(adherence["missed"], 1)
        self.assertEqual(adherence["pending"], 1)
        self.assertEqual(adherence["adherence_percentage"], 50.0)

        # Also check endpoint
        self.client.force_authenticate(user=self.doc1)
        res = self.client.get(f"/api/patient/{self.p1_profile.id}/medication-adherence/")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["total_due"], 4)
        self.assertEqual(res.data["adherence_percentage"], 50.0)

    def test_timezone_correctness_with_reference_time(self):
        """Doses scheduled near reference_time in Asia/Kolkata are picked up accurately."""
        from django.utils import timezone
        from medication.models import MedicationDose
        from medication.reminders import check_and_send_reminders

        ref_time = timezone.now()
        # Dose in 10 minutes
        near_dose = MedicationDose.objects.create(
            medication=self.med1,
            scheduled_for=ref_time + datetime.timedelta(minutes=10),
            status="pending"
        )
        # Dose 2 days later
        far_dose = MedicationDose.objects.create(
            medication=self.med1,
            scheduled_for=ref_time + datetime.timedelta(days=2),
            status="pending"
        )

        sent = check_and_send_reminders(reference_time=ref_time)
        self.assertEqual(sent, 1)

        near_dose.refresh_from_db()
        far_dose.refresh_from_db()
        self.assertIsNotNone(near_dose.reminder_sent_at)
        self.assertIsNone(far_dose.reminder_sent_at)

