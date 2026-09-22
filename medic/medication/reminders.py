import datetime
import logging
from django.utils import timezone
from .models import MedicationDose
from alerts.ws_dispatch import send_patient_notification
from alerts.models import Alert
from alerts.services import dispatch_alert_to_doctor

logger = logging.getLogger(__name__)


def check_and_send_reminders(reference_time=None, window_minutes=30):
    """
    Finds pending doses scheduled within the upcoming window (e.g. now through now + 30m)
    where reminder_sent_at is null.
    
    For each dose:
    - Pushes a real-time notification payload to the patient's WebSocket group
      (patient_<patient_id>_notifications) via send_patient_notification.
    - Sets reminder_sent_at = now so the reminder is strictly never sent twice.
    """
    now = reference_time or timezone.now()
    window_end = now + datetime.timedelta(minutes=window_minutes)

    upcoming_pending = MedicationDose.objects.filter(
        status="pending",
        reminder_sent_at__isnull=True,
        scheduled_for__gte=now,
        scheduled_for__lte=window_end
    ).select_related("medication__patient__user")

    sent_count = 0
    for dose in upcoming_pending:
        patient = dose.medication.patient
        scheduled_time_str = timezone.localtime(dose.scheduled_for).strftime("%I:%M %p")

        payload = {
            "type": "medication_reminder",
            "dose_id": dose.id,
            "medication_id": dose.medication.id,
            "medicine_name": dose.medication.medicine_name,
            "dosage": dose.medication.dosage,
            "scheduled_for": dose.scheduled_for.isoformat(),
            "scheduled_time": scheduled_time_str,
            "title": "Medication Reminder",
            "message": f"Time for {dose.medication.medicine_name} ({dose.medication.dosage}) at {scheduled_time_str}.",
        }

        # Dispatch via Phase 5 WebSocket helper
        send_patient_notification(patient.id, payload)

        # Mark reminder sent timestamp
        dose.reminder_sent_at = now
        dose.save(update_fields=["reminder_sent_at"])
        sent_count += 1

    return sent_count


def check_and_mark_missed_doses(reference_time=None, grace_period_hours=2, notify_doctor=True):
    """
    Finds doses whose scheduled_for datetime is older than now - grace_period_hours,
    and are still in 'pending' status.
    
    For each overdue dose:
    - Sets status = 'missed'.
    - Optionally creates an adherence Alert for the patient's assigned doctor.
    """
    now = reference_time or timezone.now()
    cutoff = now - datetime.timedelta(hours=grace_period_hours)

    overdue_pending = MedicationDose.objects.filter(
        status="pending",
        scheduled_for__lt=cutoff
    ).select_related("medication__patient__user", "medication__patient__doctor")

    missed_count = 0
    for dose in overdue_pending:
        dose.status = "missed"
        dose.save(update_fields=["status"])
        missed_count += 1

        patient = dose.medication.patient
        if notify_doctor and patient.doctor_id:
            alert_message = (
                f"Medication adherence alert: scheduled dose of {dose.medication.medicine_name} "
                f"({dose.medication.dosage}) past grace period was recorded as missed."
            )
            alert = Alert.objects.create(
                patient=patient,
                message=alert_message,
                severity="low"
            )
            # Dispatch to assigned doctor's isolated alert group
            dispatch_alert_to_doctor(
                patient.doctor_id,
                {
                    "alert_id": alert.id,
                    "id": alert.id,
                    "patient_id": patient.id,
                    "patient_display_name": patient.user.get_full_name() or patient.user.username,
                    "severity": alert.severity,
                    "message": alert.message,
                    "created_at": alert.created_at.isoformat(),
                }
            )

    return missed_count
