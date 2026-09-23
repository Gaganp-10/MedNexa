import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from alerts.ws_dispatch import send_patient_notification
from alerts.services import dispatch_alert_to_doctor

logger = logging.getLogger(__name__)


def dispatch_chat_events(message):
    """
    1. Broadcasts the new message to the conversation group: chat_<conversation_id>.
    2. Sends a lightweight real-time notification to the recipient's notification/alert group
       so the recipient is alerted even if they do not have the chat window open.
    All channel layer calls are safely wrapped in try/except.
    """
    conversation = message.conversation
    sender = message.sender

    # 1. Broadcast to conversation group
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"chat_{conversation.id}",
                {
                    "type": "chat_message",
                    "message": {
                        "id": message.id,
                        "conversation_id": conversation.id,
                        "sender_id": sender.id,
                        "sender_name": sender.get_full_name() or sender.username,
                        "sender_role": sender.role,
                        "content": message.content,
                        "is_read": message.is_read,
                        "created_at": message.created_at.isoformat(),
                    }
                }
            )
    except Exception as e:
        logger.error(f"WebSocket broadcast error for chat_{conversation.id}: {type(e).__name__}")

    # 2. Push lightweight notification to recipient
    try:
        # If doctor sent the message, recipient is patient
        if sender.id == conversation.doctor_id:
            patient_id = conversation.patient_id
            payload = {
                "type": "chat_message",
                "conversation_id": conversation.id,
                "message_id": message.id,
                "sender_id": sender.id,
                "sender_name": sender.get_full_name() or sender.username,
                "sender_role": "doctor",
                "message": f"Dr. {sender.get_full_name() or sender.username}: {message.content[:80]}",
                "preview": message.content[:100],
                "created_at": message.created_at.isoformat(),
            }
            send_patient_notification(patient_id, payload)
        else:
            # Patient sent the message, recipient is doctor
            doctor_id = conversation.doctor_id
            patient_name = conversation.patient.user.get_full_name() or conversation.patient.user.username
            payload = {
                "id": f"chat_{message.id}",
                "patient_id": conversation.patient_id,
                "patient_display_name": patient_name,
                "severity": "info",
                "message": f"New chat message from {patient_name}: {message.content[:80]}",
                "created_at": message.created_at.isoformat(),
                "conversation_id": conversation.id,
            }
            dispatch_alert_to_doctor(doctor_id, payload)
    except Exception as e:
        logger.error(f"Notification dispatch failure for chat message {message.id}: {type(e).__name__}")
