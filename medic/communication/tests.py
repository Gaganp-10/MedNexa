import datetime
from django.test import TransactionTestCase
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from channels.testing import WebsocketCommunicator
from asgiref.sync import sync_to_async

from accounts.models import User, DoctorProfile, PatientProfile
from communication.models import Conversation, Message
from medic.asgi import application


class CommunicationRestApiTests(TransactionTestCase):
    def setUp(self):
        self.client = APIClient()

        # Doctor 1 & 2
        self.doc1 = User.objects.create_user(
            username="comm_doc1", password="password123", role="doctor"
        )
        self.doc1_profile = DoctorProfile.objects.create(
            user=self.doc1, specialization="Orthopedics"
        )

        self.doc2 = User.objects.create_user(
            username="comm_doc2", password="password123", role="doctor"
        )
        self.doc2_profile = DoctorProfile.objects.create(
            user=self.doc2, specialization="Cardiology"
        )

        # Patient 1 (assigned to doc1)
        self.p1_user = User.objects.create_user(
            username="comm_p1", password="password123", role="patient"
        )
        self.p1_profile = PatientProfile.objects.create(
            user=self.p1_user,
            surgery_type="Hip Replacement",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc1
        )

        # Patient 2 (assigned to doc2)
        self.p2_user = User.objects.create_user(
            username="comm_p2", password="password123", role="patient"
        )
        self.p2_profile = PatientProfile.objects.create(
            user=self.p2_user,
            surgery_type="Heart Bypass",
            surgery_date=datetime.date(2026, 3, 2),
            doctor=self.doc2
        )

        # Patient 3 (assigned to doc1, but no conversation initially)
        self.p3_user = User.objects.create_user(
            username="comm_p3", password="password123", role="patient"
        )
        self.p3_profile = PatientProfile.objects.create(
            user=self.p3_user,
            surgery_type="Spinal Fusion",
            surgery_date=datetime.date(2026, 3, 3),
            doctor=self.doc1
        )

        # Conversation 1: doc1 <-> p1
        self.conv1 = Conversation.objects.create(
            doctor=self.doc1,
            patient=self.p1_profile
        )

        # Conversation 2: doc2 <-> p2
        self.conv2 = Conversation.objects.create(
            doctor=self.doc2,
            patient=self.p2_profile
        )

    def test_empty_conversation_returns_empty_list_200(self):
        """A conversation with zero messages returns an empty list (200 OK), not an error."""
        self.client.force_authenticate(user=self.doc1)
        url = f"/api/communication/conversations/{self.conv1.id}/messages/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["count"], 0)
        self.assertEqual(res.data["results"], [])

    def test_unassigned_doctor_cannot_read_or_send_404(self):
        """Doctor 2 cannot read or send messages in Doctor 1's patient conversation."""
        self.client.force_authenticate(user=self.doc2)
        url = f"/api/communication/conversations/{self.conv1.id}/messages/"

        # Read attempt -> 404
        res_read = self.client.get(url)
        self.assertEqual(res_read.status_code, status.HTTP_404_NOT_FOUND)

        # Send attempt -> 404
        res_send = self.client.post(url, {"content": "Unauthorized message"}, format="json")
        self.assertEqual(res_send.status_code, status.HTTP_404_NOT_FOUND)

    def test_patient_cannot_access_other_patient_conversation_404(self):
        """Patient 2 cannot access Patient 1's conversation."""
        self.client.force_authenticate(user=self.p2_user)
        url = f"/api/communication/conversations/{self.conv1.id}/messages/"

        # Read attempt -> 404
        res_read = self.client.get(url)
        self.assertEqual(res_read.status_code, status.HTTP_404_NOT_FOUND)

        # Send attempt -> 404
        res_send = self.client.post(url, {"content": "Intruder message"}, format="json")
        self.assertEqual(res_send.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_conversation_message_isolation(self):
        """Messages in Conversation 1 never leak or appear in Conversation 2."""
        self.client.force_authenticate(user=self.doc1)
        res1 = self.client.post(
            f"/api/communication/conversations/{self.conv1.id}/messages/",
            {"content": "Private note for patient 1"},
            format="json"
        )
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        self.client.force_authenticate(user=self.doc2)
        res2 = self.client.post(
            f"/api/communication/conversations/{self.conv2.id}/messages/",
            {"content": "Private note for patient 2"},
            format="json"
        )
        self.assertEqual(res2.status_code, status.HTTP_201_CREATED)

        # Doc1 reads Conv1
        self.client.force_authenticate(user=self.doc1)
        list1 = self.client.get(f"/api/communication/conversations/{self.conv1.id}/messages/")
        contents1 = [m["content"] for m in list1.data["results"]]
        self.assertIn("Private note for patient 1", contents1)
        self.assertNotIn("Private note for patient 2", contents1)

        # Doc2 reads Conv2
        self.client.force_authenticate(user=self.doc2)
        list2 = self.client.get(f"/api/communication/conversations/{self.conv2.id}/messages/")
        contents2 = [m["content"] for m in list2.data["results"]]
        self.assertIn("Private note for patient 2", contents2)
        self.assertNotIn("Private note for patient 1", contents2)

    def test_empty_or_whitespace_message_rejected_400(self):
        """Sending empty or whitespace-only message returns a clear 400 validation error."""
        self.client.force_authenticate(user=self.doc1)
        url = f"/api/communication/conversations/{self.conv1.id}/messages/"

        # Empty string
        res_empty = self.client.post(url, {"content": ""}, format="json")
        self.assertEqual(res_empty.status_code, status.HTTP_400_BAD_REQUEST)

        # Whitespace only
        res_ws = self.client.post(url, {"content": "   \n\t  "}, format="json")
        self.assertEqual(res_ws.status_code, status.HTTP_400_BAD_REQUEST)

    def test_sender_integrity_enforced(self):
        """Sender is always request.user; spoofed sender fields in payload are ignored."""
        self.client.force_authenticate(user=self.doc1)
        url = f"/api/communication/conversations/{self.conv1.id}/messages/"
        res = self.client.post(
            url,
            {"content": "Testing sender", "sender": self.doc2.id, "sender_id": self.doc2.id},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["sender_id"], self.doc1.id)

    def test_read_receipt_only_settable_by_recipient(self):
        """Only the recipient (not the sender or unrelated users) can mark a message read."""
        # Doc1 sends message to P1
        self.client.force_authenticate(user=self.doc1)
        send_res = self.client.post(
            f"/api/communication/conversations/{self.conv1.id}/messages/",
            {"content": "Take medication after dinner"},
            format="json"
        )
        msg_id = send_res.data["id"]

        # Sender (doc1) attempts to mark read -> 403 Forbidden
        patch_res_sender = self.client.patch(f"/api/communication/messages/{msg_id}/read/")
        self.assertEqual(patch_res_sender.status_code, status.HTTP_403_FORBIDDEN)

        # Unrelated doc (doc2) attempts to mark read -> 404 Not Found
        self.client.force_authenticate(user=self.doc2)
        patch_res_other = self.client.patch(f"/api/communication/messages/{msg_id}/read/")
        self.assertEqual(patch_res_other.status_code, status.HTTP_404_NOT_FOUND)

        # Recipient (p1) marks read -> 200 OK
        self.client.force_authenticate(user=self.p1_user)
        patch_res_recipient = self.client.patch(f"/api/communication/messages/{msg_id}/read/")
        self.assertEqual(patch_res_recipient.status_code, status.HTTP_200_OK)
        self.assertTrue(patch_res_recipient.data["is_read"])

    def test_auto_creation_of_conversation_on_first_message(self):
        """Conversation is automatically created on first message send without prior setup."""
        self.client.force_authenticate(user=self.doc1)

        # Verify no conversation exists between doc1 and p3 initially
        self.assertFalse(
            Conversation.objects.filter(doctor=self.doc1, patient=self.p3_profile).exists()
        )

        # Post first message to patient endpoint
        res = self.client.post(
            f"/api/communication/conversations/{self.p3_profile.id}/messages/",
            {"content": "Welcome to MedNexa! How are your vitals today?"},
            format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        # Conversation now exists
        conv = Conversation.objects.filter(doctor=self.doc1, patient=self.p3_profile).first()
        self.assertIsNotNone(conv)
        self.assertEqual(conv.messages.count(), 1)
        self.assertEqual(conv.messages.first().content, "Welcome to MedNexa! How are your vitals today?")

    def test_doctor_assignment_removed_cannot_access_or_send_404(self):
        """A doctor whose assignment was removed can no longer read or send messages (behaves as 404)."""
        # Create an initial message while assigned
        self.client.force_authenticate(user=self.doc1)
        self.client.post(
            f"/api/communication/conversations/{self.conv1.id}/messages/",
            {"content": "First message before discharge"},
            format="json"
        )

        # Remove doctor assignment from patient
        self.p1_profile.doctor = None
        self.p1_profile.save()

        # Doctor 1 attempts to read -> 404
        res_read = self.client.get(f"/api/communication/conversations/{self.conv1.id}/messages/")
        self.assertEqual(res_read.status_code, status.HTTP_404_NOT_FOUND)

        # Doctor 1 attempts to send -> 404
        res_send = self.client.post(
            f"/api/communication/conversations/{self.conv1.id}/messages/",
            {"content": "Message after unassignment"},
            format="json"
        )
        self.assertEqual(res_send.status_code, status.HTTP_404_NOT_FOUND)

        # Conversation list does not include it
        res_list = self.client.get("/api/communication/conversations/")
        self.assertEqual(res_list.status_code, status.HTTP_200_OK)
        conv_ids = [c["id"] for c in res_list.data["results"]]
        self.assertNotIn(self.conv1.id, conv_ids)


class CommunicationWebSocketTests(TransactionTestCase):
    def setUp(self):
        # Doctor 1
        self.doc1 = User.objects.create_user(
            username="ws_chat_doc1", password="password123", role="doctor"
        )
        self.doc1_profile = DoctorProfile.objects.create(
            user=self.doc1, specialization="General Surgery"
        )

        # Doctor 2
        self.doc2 = User.objects.create_user(
            username="ws_chat_doc2", password="password123", role="doctor"
        )
        self.doc2_profile = DoctorProfile.objects.create(
            user=self.doc2, specialization="Plastic Surgery"
        )

        # Patient 1 (assigned to doc1)
        self.p1_user = User.objects.create_user(
            username="ws_chat_p1", password="password123", role="patient"
        )
        self.p1_profile = PatientProfile.objects.create(
            user=self.p1_user,
            surgery_type="Appendectomy",
            surgery_date=datetime.date(2026, 3, 1),
            doctor=self.doc1
        )

        # Patient 2 (assigned to doc2)
        self.p2_user = User.objects.create_user(
            username="ws_chat_p2", password="password123", role="patient"
        )
        self.p2_profile = PatientProfile.objects.create(
            user=self.p2_user,
            surgery_type="Gallbladder",
            surgery_date=datetime.date(2026, 3, 2),
            doctor=self.doc2
        )

        self.conv1 = Conversation.objects.create(
            doctor=self.doc1,
            patient=self.p1_profile
        )

    def _get_token(self, user):
        return str(AccessToken.for_user(user))

    async def test_ws_connect_unauthenticated_rejected_4401(self):
        """Connecting to ws/chat/<conv_id>/ without a token must close with code 4401."""
        comm = WebsocketCommunicator(application, f"/ws/chat/{self.conv1.id}/")
        connected, close_code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4401)

    async def test_ws_connect_non_participant_rejected_4403(self):
        """Unassigned doctor and unrelated patient connecting to ws/chat/<conv_id>/ close with 4403."""
        doc2_token = self._get_token(self.doc2)
        comm_doc2 = WebsocketCommunicator(application, f"/ws/chat/{self.conv1.id}/?token={doc2_token}")
        connected, close_code = await comm_doc2.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)

        p2_token = self._get_token(self.p2_user)
        comm_p2 = WebsocketCommunicator(application, f"/ws/chat/{self.conv1.id}/?token={p2_token}")
        connected, close_code = await comm_p2.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)

    async def test_ws_connect_unassigned_doctor_previously_assigned_rejected_4403(self):
        """WebSocket connect rejected with 4403 for doctor whose assignment was removed."""
        # Remove doc1 assignment
        self.p1_profile.doctor = None
        await sync_to_async(self.p1_profile.save)()

        doc1_token = self._get_token(self.doc1)
        comm = WebsocketCommunicator(application, f"/ws/chat/{self.conv1.id}/?token={doc1_token}")
        connected, close_code = await comm.connect()
        self.assertFalse(connected)
        self.assertEqual(close_code, 4403)

    async def test_ws_connect_success_and_broadcast(self):
        """Both participants connect and receive messages broadcasted to chat_<conv_id>."""
        doc1_token = self._get_token(self.doc1)
        p1_token = self._get_token(self.p1_user)

        comm_doc = WebsocketCommunicator(application, f"/ws/chat/{self.conv1.id}/?token={doc1_token}")
        comm_pat = WebsocketCommunicator(application, f"/ws/chat/{self.conv1.id}/?token={p1_token}")

        conn_doc, _ = await comm_doc.connect()
        conn_pat, _ = await comm_pat.connect()
        self.assertTrue(conn_doc)
        self.assertTrue(conn_pat)

        # Patient sends a message via WebSocket
        await comm_pat.send_json_to({"content": "Hello doctor, my pain is decreasing."})

        # Both doctor and patient should receive the broadcast
        msg_doc = await comm_doc.receive_json_from(timeout=3)
        msg_pat = await comm_pat.receive_json_from(timeout=3)

        self.assertEqual(msg_doc["content"], "Hello doctor, my pain is decreasing.")
        self.assertEqual(msg_pat["content"], "Hello doctor, my pain is decreasing.")
        self.assertEqual(msg_doc["conversation_id"], self.conv1.id)

        # Confirm persisted in DB
        persisted = await sync_to_async(
            Message.objects.filter(conversation=self.conv1, content="Hello doctor, my pain is decreasing.").first
        )()
        self.assertIsNotNone(persisted)

        await comm_doc.disconnect()
        await comm_pat.disconnect()

    async def test_chat_message_triggers_recipient_notification(self):
        """Sending a chat message dispatches a lightweight notification to recipient's notification group."""
        p1_token = self._get_token(self.p1_user)
        # Patient listens to general notifications endpoint
        notif_comm = WebsocketCommunicator(application, f"/ws/notifications/?token={p1_token}")
        connected, _ = await notif_comm.connect()
        self.assertTrue(connected)

        # Doctor sends message via REST API
        client = APIClient()
        client.force_authenticate(user=self.doc1)
        await sync_to_async(client.post)(
            f"/api/communication/conversations/{self.conv1.id}/messages/",
            {"content": "Remember to take your antibiotic at 8 PM."},
            format="json"
        )

        # Patient's notification socket receives alert
        notif = await notif_comm.receive_json_from(timeout=3)
        self.assertEqual(notif["type"], "chat_message")
        self.assertEqual(notif["conversation_id"], self.conv1.id)
        self.assertIn("antibiotic", notif["preview"])

        await notif_comm.disconnect()
