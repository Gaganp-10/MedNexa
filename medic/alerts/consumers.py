import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from accounts.models import DoctorProfile, PatientProfile


@database_sync_to_async
def get_doctor_profile_exists(user):
    return DoctorProfile.objects.filter(user=user).exists()


@database_sync_to_async
def get_patient_profile_id(user):
    profile = PatientProfile.objects.filter(user=user).first()
    return profile.id if profile else None


class AlertConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for doctor alerts on ws/alerts/.
    Doctors connect and are added strictly to group: doctor_<user.id>_alerts.
    Any non-doctor or user without a matching DoctorProfile is rejected with code 4403.
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        if user.role != "doctor":
            await self.close(code=4403)
            return

        has_profile = await get_doctor_profile_exists(user)
        if not has_profile:
            await self.close(code=4403)
            return

        self.group_name = f"doctor_{user.id}_alerts"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name") and self.channel_layer:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_alert(self, event):
        await self.send(text_data=json.dumps({
            "id": event.get("alert_id") or event.get("id"),
            "patient_id": event.get("patient_id"),
            "patient_display_name": event.get("patient_display_name"),
            "severity": event.get("severity"),
            "message": event.get("message"),
            "created_at": event.get("created_at"),
        }))


class PatientNotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for patient notifications on ws/notifications/.
    Patients connect and are added strictly to group: patient_<patientprofile.id>_notifications.
    Any non-patient or user without a matching PatientProfile is rejected with code 4403.
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        if user.role != "patient":
            await self.close(code=4403)
            return

        patient_profile_id = await get_patient_profile_id(user)
        if not patient_profile_id:
            await self.close(code=4403)
            return

        self.group_name = f"patient_{patient_profile_id}_notifications"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name") and self.channel_layer:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def send_notification(self, event):
        payload = event.get("payload", event)
        await self.send(text_data=json.dumps(payload))