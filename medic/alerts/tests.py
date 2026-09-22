import datetime
from django.test import TransactionTestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from channels.testing import WebsocketCommunicator
from asgiref.sync import sync_to_async

from accounts.models import User, DoctorProfile, PatientProfile
from alerts.models import Alert
from alerts.services import analyze_health_log, dispatch_alert_to_doctor
from alerts.ws_dispatch import send_patient_notification
from monitoring.models import DailyHealthLog
from medic.asgi import application


class AlertRestApiTests(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()

        # Doctors
        self.doc1 = User.objects.create_user(
            username="alert_doc1", password="password123", role="doctor"
        )
        self.doc1_profile = DoctorProfile.objects.create(
            user=self.doc1, specialization="Cardiology"
        )

        self.doc2 = User.objects.create_user(
            username="alert_doc2", password="password123", role="doctor"
        )
        self.doc2_profile = DoctorProfile.objects.create(
            user=self.doc2, specialization="Neurology"
        )

        # Patient 1 (assigned to doc1)
        self.p1_user = User.objects.create_user(
            username="alert_p1", password="password123", role="patient"
        )
        self.p1_profile = PatientProfile.objects.create(
            user=self.p1_user,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc1
        )

        # Patient 2 (assigned to doc2)
        self.p2_user = User.objects.create_user(
            username="alert_p2", password="password123", role="patient"
        )
        self.p2_profile = PatientProfile.objects.create(
            user=self.p2_user,
            surgery_type="Knee Surgery",
            surgery_date=datetime.date(2026, 3, 2),
            doctor=self.doc2
        )

        # Alert for Patient 1
        self.alert1 = Alert.objects.create(
            patient=self.p1_profile,
            message="Test high fever alert",
            severity="high"
        )

    def test_alert_mark_read_assigned_doctor_success(self):
        """Assigned doctor can mark their patient's alert as read."""
        self.client.force_authenticate(user=self.doc1)
        url = f"/api/alerts/{self.alert1.id}/read/"

        response = self.client.patch(url, {"is_read": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alert1.refresh_from_db()
        self.assertTrue(self.alert1.is_read)

    def test_alert_mark_read_unassigned_doctor_404(self):
        """Unassigned doctor receives 404 when attempting to mark alert as read."""
        self.client.force_authenticate(user=self.doc2)
        url = f"/api/alerts/{self.alert1.id}/read/"

        response = self.client.patch(url, {"is_read": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.alert1.refresh_from_db()
        self.assertFalse(self.alert1.is_read)

    def test_alert_mark_read_patient_404(self):
        """Patient receives 404 when attempting to mark alert as read (even for self)."""
        self.client.force_authenticate(user=self.p1_user)
        url = f"/api/alerts/{self.alert1.id}/read/"

        response = self.client.patch(url, {"is_read": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_alert_mark_read_only_is_read_is_writable(self):
        """Attempts to modify other fields (e.g. message, severity) are ignored."""
        self.client.force_authenticate(user=self.doc1)
        url = f"/api/alerts/{self.alert1.id}/read/"

        response = self.client.patch(
            url,
            {"is_read": True, "message": "Tampered message", "severity": "low"},
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alert1.refresh_from_db()
        self.assertTrue(self.alert1.is_read)
        self.assertEqual(self.alert1.message, "Test high fever alert")
        self.assertEqual(self.alert1.severity, "high")


class AlertWebSocketSecurityTests(TransactionTestCase):
    def setUp(self):
        # Doctor 1 & Doctor 2
        self.doc1 = User.objects.create_user(
            username="ws_doc1", password="password123", role="doctor", first_name="DrOne"
        )
        self.doc1_profile = DoctorProfile.objects.create(
            user=self.doc1, specialization="Cardiology"
        )

        self.doc2 = User.objects.create_user(
            username="ws_doc2", password="password123", role="doctor", first_name="DrTwo"
        )
        self.doc2_profile = DoctorProfile.objects.create(
            user=self.doc2, specialization="Neurology"
        )

        # Patient 1 (assigned to doc1)
        self.p1_user = User.objects.create_user(
            username="ws_p1", password="password123", role="patient", first_name="PatientOne"
        )
        self.p1_profile = PatientProfile.objects.create(
            user=self.p1_user,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc1
        )

        # Patient 2 (no assigned doctor)
        self.p2_user = User.objects.create_user(
            username="ws_p2", password="password123", role="patient", first_name="PatientTwo"
        )
        self.p2_profile = PatientProfile.objects.create(
            user=self.p2_user,
            surgery_type="Cholecystectomy",
            surgery_date=datetime.date(2026, 3, 5),
            doctor=None
        )

    def _get_token(self, user):
        return str(AccessToken.for_user(user))

    async def test_unauthenticated_connection_rejected_4401(self):
        """Connecting without a token must be rejected with close code 4401."""
        communicator = WebsocketCommunicator(application, "/ws/alerts/")
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_invalid_token_rejected_4401(self):
        """Connecting with an invalid token must be rejected with close code 4401."""
        communicator = WebsocketCommunicator(application, "/ws/alerts/?token=invalid_token_123")
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_patient_cannot_connect_to_ws_alerts_4403(self):
        """Patients connecting to doctor alerts endpoint ws/alerts/ must be closed with 4403."""
        token = self._get_token(self.p1_user)
        communicator = WebsocketCommunicator(application, f"/ws/alerts/?token={token}")
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)

    async def test_doctor_cannot_connect_to_ws_notifications_4403(self):
        """Doctors connecting to patient notifications endpoint ws/notifications/ must be closed with 4403."""
        token = self._get_token(self.doc1)
        communicator = WebsocketCommunicator(application, f"/ws/notifications/?token={token}")
        connected, close_code = await communicator.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)

    async def test_doctor_receives_alert_for_assigned_patient(self):
        """Doctor receives an alert generated for their assigned patient."""
        doc1_token = self._get_token(self.doc1)
        communicator = WebsocketCommunicator(application, f"/ws/alerts/?token={doc1_token}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Generate alert for Patient 1 (assigned to doc1)
        log = await sync_to_async(DailyHealthLog.objects.create)(
            patient=self.p1_profile,
            temperature=39.5,
            pain_level=7,
            medication_taken=True
        )
        await sync_to_async(analyze_health_log)(log)

        # Doctor 1 should receive message
        message = await communicator.receive_json_from(timeout=2)
        self.assertEqual(message["patient_id"], self.p1_profile.id)
        self.assertEqual(message["severity"], "high")
        self.assertIn("patient_display_name", message)
        self.assertIn("id", message)
        self.assertIn("created_at", message)

        await communicator.disconnect()

    async def test_second_doctor_does_not_receive_alert(self):
        """A second doctor connected at the same time does NOT receive the other doctor's alert."""
        doc1_token = self._get_token(self.doc1)
        doc2_token = self._get_token(self.doc2)

        comm1 = WebsocketCommunicator(application, f"/ws/alerts/?token={doc1_token}")
        comm2 = WebsocketCommunicator(application, f"/ws/alerts/?token={doc2_token}")

        conn1, _ = await comm1.connect()
        conn2, _ = await comm2.connect()
        self.assertTrue(conn1)
        self.assertTrue(conn2)

        # Generate alert for Patient 1 (assigned ONLY to doc1)
        log = await sync_to_async(DailyHealthLog.objects.create)(
            patient=self.p1_profile,
            temperature=39.8,
            pain_level=5,
            medication_taken=True
        )
        await sync_to_async(analyze_health_log)(log)

        # Doctor 1 receives it
        msg1 = await comm1.receive_json_from(timeout=2)
        self.assertEqual(msg1["patient_id"], self.p1_profile.id)

        # Doctor 2 should receive nothing
        nothing_received = await comm2.receive_nothing(timeout=0.5)
        self.assertTrue(nothing_received)

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_alert_for_patient_with_no_doctor_does_not_raise(self):
        """Creating an alert for a patient with no assigned doctor skips cleanly without error."""
        log = await sync_to_async(DailyHealthLog.objects.create)(
            patient=self.p2_profile,
            temperature=40.0,
            pain_level=10,
            medication_taken=False
        )
        created_alerts = await sync_to_async(analyze_health_log)(log)
        self.assertTrue(len(created_alerts) > 0)
        # Check Alert records exist in DB
        self.assertEqual(await sync_to_async(Alert.objects.filter(patient=self.p2_profile).count)(), len(created_alerts))

    async def test_patient_receives_ws_notification(self):
        """Patient connects to ws/notifications/ and receives dispatched notification."""
        p1_token = self._get_token(self.p1_user)
        communicator = WebsocketCommunicator(application, f"/ws/notifications/?token={p1_token}")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        test_payload = {"title": "Medication Reminder", "body": "Take Amoxicillin 500mg"}
        await sync_to_async(send_patient_notification)(self.p1_profile.id, test_payload)

        msg = await communicator.receive_json_from(timeout=2)
        self.assertEqual(msg["title"], "Medication Reminder")
        self.assertEqual(msg["body"], "Take Amoxicillin 500mg")

        await communicator.disconnect()
