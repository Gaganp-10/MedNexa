import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Conversation, Message
from .services import dispatch_chat_events

logger = logging.getLogger(__name__)


@database_sync_to_async
def verify_conversation_access(conversation_id, user):
    """
    Verifies that:
    1. Conversation exists.
    2. User is either the doctor or the patient.
    3. The doctor is currently assigned to this patient.
    """
    if not user or not user.is_authenticated:
        return None, False

    try:
        conversation = (
            Conversation.objects
            .select_related("doctor", "patient__user", "patient__doctor")
            .get(id=conversation_id)
        )
    except (Conversation.DoesNotExist, ValueError):
        return None, False

    is_doctor = (conversation.doctor_id == user.id)
    is_patient = (conversation.patient.user_id == user.id)

    if not (is_doctor or is_patient):
        return conversation, False

    # Check whether the doctor is currently assigned to the patient
    if conversation.patient.doctor_id != conversation.doctor_id:
        return conversation, False

    return conversation, True


@database_sync_to_async
def save_chat_message(conversation_id, user, raw_content):
    """
    Persists a chat message to DB after validating content and current assignment.
    """
    stripped = raw_content.strip() if raw_content else ""
    if not stripped:
        raise ValueError("Message content cannot be blank or whitespace only.")
    if len(stripped) > 4000:
        raise ValueError("Message content exceeds 4000 characters.")

    conversation = (
        Conversation.objects
        .select_related("doctor", "patient__user")
        .get(id=conversation_id)
    )
    if conversation.patient.doctor_id != conversation.doctor_id:
        raise PermissionError("Doctor is no longer assigned to this patient.")

    msg = Message.objects.create(
        conversation=conversation,
        sender=user,
        content=stripped
    )
    conversation.save(update_fields=["updated_at"])
    return msg


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time chat on ws/chat/<conversation_id>/.
    Rejects non-participants and unassigned doctors with close code 4403.
    Persists incoming socket messages to DB first, then broadcasts to group and notifies recipient.
    """

    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close(code=4401)
            return

        self.conversation_id = self.scope["url_route"]["kwargs"].get("conversation_id")
        conversation, is_authorized = await verify_conversation_access(self.conversation_id, user)

        if not is_authorized:
            await self.close(code=4403)
            return

        self.group_name = f"chat_{self.conversation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if hasattr(self, "group_name") and self.channel_layer:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        """
        Handles incoming messages sent directly via WebSocket.
        Persists to database first, then triggers group broadcast & notification.
        """
        if not text_data:
            return

        try:
            data = json.loads(text_data)
        except Exception:
            await self.send(text_data=json.dumps({"error": "Invalid JSON format."}))
            return

        content = data.get("content") or data.get("message")
        user = self.scope.get("user")

        try:
            msg = await save_chat_message(self.conversation_id, user, content)
            await database_sync_to_async(dispatch_chat_events)(msg)
        except (ValueError, PermissionError) as err:
            await self.send(text_data=json.dumps({"error": str(err)}))
        except Exception as e:
            logger.error(f"Error persisting socket chat message: {type(e).__name__}")
            await self.send(text_data=json.dumps({"error": "Failed to send message."}))

    async def chat_message(self, event):
        """
        Broadcasts message payload to connected client.
        """
        message = event.get("message", event)
        await self.send(text_data=json.dumps(message))
