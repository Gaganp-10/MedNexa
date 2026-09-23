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


class AlertThresholdBoundaryTests(TransactionTestCase):
    """
    Phase 7 gap: test each alert threshold on both sides of the boundary.

    Thresholds (from alerts/services.py):
      Temperature:
        > 39.0  → high alert ("urgent")
        > 38.0  → high alert ("elevated") [if not already > 39.0]
        ≤ 38.0  → no temperature alert
      Pain:
        > 9     → high alert
        > 8     → medium alert [if not already > 9]
        ≤ 8     → no pain alert
      Medication:
        not taken → low alert
        taken     → no medication alert
    """

    def setUp(self):
        self.p_user = User.objects.create_user(
            username="thresh_p", password="pass", role="patient"
        )
        self.p_profile = PatientProfile.objects.create(
            user=self.p_user,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=None  # no doctor: no WS dispatch, just DB alert creation
        )

    def _make_log(self, temp, pain, med_taken=True):
        return DailyHealthLog.objects.create(
            patient=self.p_profile,
            temperature=temp,
            pain_level=pain,
            medication_taken=med_taken
        )

    # ── Temperature boundary ───────────────────────────────────────────────────

    def test_temp_exactly_38_no_alert(self):
        """Temperature exactly 38.0 must NOT generate a temperature alert."""
        Alert.objects.all().delete()
        log = self._make_log(38.0, 5)
        alerts = analyze_health_log(log)
        temp_alerts = [a for a in alerts if "temperature" in a.message.lower()]
        self.assertEqual(len(temp_alerts), 0,
                         "Temperature 38.0 is not > 38.0, so no alert expected")

    def test_temp_just_above_38_generates_elevated_alert(self):
        """Temperature 38.01 (just above 38.0) must generate an elevated temperature alert."""
        Alert.objects.all().delete()
        log = self._make_log(38.01, 5)
        alerts = analyze_health_log(log)
        temp_alerts = [a for a in alerts if "temperature" in a.message.lower()]
        self.assertGreater(len(temp_alerts), 0,
                           "Temperature 38.01 is > 38.0, should trigger elevated alert")

    def test_temp_exactly_39_no_urgent_alert(self):
        """
        Temperature exactly 39.0 is NOT > 39.0 so must NOT generate the urgent ('high fever') alert.
        It IS > 38.0 so it generates the 'elevated' alert instead.
        """
        Alert.objects.all().delete()
        log = self._make_log(39.0, 5)
        alerts = analyze_health_log(log)
        # Should have at most one temperature alert and it should be the 'elevated' one
        temp_alerts = [a for a in alerts if "temperature" in a.message.lower()]
        self.assertEqual(len(temp_alerts), 1)
        self.assertNotIn("urgent", temp_alerts[0].message.lower())

    def test_temp_just_above_39_generates_urgent_alert(self):
        """Temperature 39.01 (just above 39.0) must generate the urgent temperature alert."""
        Alert.objects.all().delete()
        log = self._make_log(39.01, 5)
        alerts = analyze_health_log(log)
        temp_alerts = [a for a in alerts if "temperature" in a.message.lower()]
        self.assertGreater(len(temp_alerts), 0)
        # At least one should be 'urgent'
        urgent = [a for a in temp_alerts if "urgent" in a.message.lower()]
        self.assertGreater(len(urgent), 0,
                           "Temperature 39.01 should trigger urgent alert")

    # ── Pain boundary ──────────────────────────────────────────────────────────

    def test_pain_exactly_8_no_pain_alert(self):
        """Pain level exactly 8 must NOT generate any pain alert."""
        Alert.objects.all().delete()
        log = self._make_log(37.0, 8)
        alerts = analyze_health_log(log)
        pain_alerts = [a for a in alerts if "pain" in a.message.lower()]
        self.assertEqual(len(pain_alerts), 0,
                         "Pain 8 is not > 8, so no pain alert expected")

    def test_pain_exactly_9_generates_medium_alert(self):
        """Pain level exactly 9 is > 8 but not > 9: must generate a medium pain alert."""
        Alert.objects.all().delete()
        log = self._make_log(37.0, 9)
        alerts = analyze_health_log(log)
        pain_alerts = [a for a in alerts if "pain" in a.message.lower()]
        self.assertGreater(len(pain_alerts), 0, "Pain 9 > 8, should trigger alert")
        # Should be medium, not urgent
        self.assertFalse(
            any("urgent" in a.message.lower() for a in pain_alerts),
            "Pain 9 is not > 9, should not be urgent"
        )

    def test_pain_exactly_10_generates_high_urgent_alert(self):
        """Pain level 10 is > 9: must generate the urgent (high severity) pain alert."""
        Alert.objects.all().delete()
        log = self._make_log(37.0, 10)
        alerts = analyze_health_log(log)
        pain_alerts = [a for a in alerts if "pain" in a.message.lower()]
        self.assertGreater(len(pain_alerts), 0, "Pain 10 > 9, should trigger alert")
        urgent = [a for a in pain_alerts if "urgent" in a.message.lower()]
        self.assertGreater(len(urgent), 0, "Pain 10 should produce urgent alert")

    # ── Medication taken boundary ──────────────────────────────────────────────

    def test_medication_taken_true_no_adherence_alert(self):
        """medication_taken=True must not generate a medication adherence alert."""
        Alert.objects.all().delete()
        log = self._make_log(37.0, 3, med_taken=True)
        alerts = analyze_health_log(log)
        med_alerts = [a for a in alerts if "medication" in a.message.lower() or "adherence" in a.message.lower()]
        self.assertEqual(len(med_alerts), 0,
                         "medication_taken=True should not generate adherence alert")

    def test_medication_not_taken_generates_low_alert(self):
        """medication_taken=False must generate a low-severity medication adherence alert."""
        Alert.objects.all().delete()
        log = self._make_log(37.0, 3, med_taken=False)
        alerts = analyze_health_log(log)
        med_alerts = [a for a in alerts if "medication" in a.message.lower() or "adherence" in a.message.lower()]
        self.assertGreater(len(med_alerts), 0,
                           "medication_taken=False should generate adherence alert")
        self.assertEqual(med_alerts[0].severity, "low")


class WebSocketExpiredTokenTests(TransactionTestCase):
    """
    Phase 7 gap: verify expired tokens are rejected on all three WS consumers.
    """

    def setUp(self):
        self.doc = User.objects.create_user(
            username="exp_doc", password="pass", role="doctor"
        )
        DoctorProfile.objects.create(user=self.doc, specialization="Surgery")
        self.patient = User.objects.create_user(
            username="exp_patient", password="pass", role="patient"
        )
        self.p_profile = PatientProfile.objects.create(
            user=self.patient,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc
        )
        self.conv = None  # created lazily

    def _get_expired_token(self, user):
        """Generate an already-expired access token by manipulating lifetime."""
        import datetime as dt
        from rest_framework_simplejwt.tokens import AccessToken as AT
        from rest_framework_simplejwt.settings import api_settings
        token = AT.for_user(user)
        # Backdate the expiry to make it expired
        token.set_exp(
            claim="exp",
            from_time=dt.datetime.now(tz=dt.timezone.utc) - dt.timedelta(hours=2),
            lifetime=dt.timedelta(seconds=1)
        )
        return str(token)

    async def test_expired_token_rejected_alerts_4401(self):
        """Expired token on /ws/alerts/ must close with code 4401."""
        token = self._get_expired_token(self.doc)
        comm = WebsocketCommunicator(application, f"/ws/alerts/?token={token}")
        connected, close_code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_expired_token_rejected_notifications_4401(self):
        """Expired token on /ws/notifications/ must close with code 4401."""
        token = self._get_expired_token(self.patient)
        comm = WebsocketCommunicator(application, f"/ws/notifications/?token={token}")
        connected, close_code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_expired_token_rejected_chat_4401(self):
        """Expired token on /ws/chat/<conv_id>/ must close with code 4401."""
        # Create conversation synchronously
        from communication.models import Conversation
        conv = await sync_to_async(Conversation.objects.create)(
            doctor=self.doc, patient=self.p_profile
        )
        token = self._get_expired_token(self.doc)
        comm = WebsocketCommunicator(application, f"/ws/chat/{conv.id}/?token={token}")
        connected, close_code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_missing_token_notifications_rejected_4401(self):
        """Connecting to /ws/notifications/ without a token must close with 4401."""
        comm = WebsocketCommunicator(application, "/ws/notifications/")
        connected, close_code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)
