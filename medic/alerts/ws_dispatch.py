"""
WebSocket dispatch helper for patient notifications.
Reusable across alerts, medication reminders, and future chat systems.
"""
import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)


def send_patient_notification(patient_id, payload):
    """
    Pushes a notification message to a patient's WebSocket notification group:
    patient_<patient_id>_notifications.

    Wrapped in try/except with safe logging so delivery errors never propagate
    to callers or crash API requests.
    """
    if not patient_id:
        return

    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            async_to_sync(channel_layer.group_send)(
                f"patient_{patient_id}_notifications",
                {
                    "type": "send_notification",
                    "payload": payload,
                }
            )
    except Exception as e:
        logger.error(f"WebSocket delivery failure in patient notification dispatch: {type(e).__name__}")
