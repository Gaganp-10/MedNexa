import datetime
from django.utils import timezone
from .models import Medication, MedicationDose


def generate_upcoming_doses(medication, days=7, start_date=None):
    """
    Generates upcoming MedicationDose rows for the given Medication over a date window.
    Guaranteed idempotent via the (medication, scheduled_for) unique constraint and get_or_create.
    Never duplicates doses.
    """
    if start_date is None:
        start_date = timezone.localdate()

    tz = timezone.get_current_timezone()
    created_or_found = []

    for offset in range(days):
        target_date = start_date + datetime.timedelta(days=offset)
        naive_dt = datetime.datetime.combine(target_date, medication.time)
        scheduled_for = timezone.make_aware(naive_dt, tz)

        dose, created = MedicationDose.objects.get_or_create(
            medication=medication,
            scheduled_for=scheduled_for,
            defaults={"status": "pending"}
        )
        created_or_found.append(dose)

    return created_or_found


def calculate_patient_adherence(patient_profile, window_days=7, reference_time=None):
    """
    Computes medication adherence metrics for a patient over a historical evaluation window.
    Considers doses scheduled up to reference_time (defaults to timezone.now()).
    """
    ref_time = reference_time or timezone.now()
    start_time = ref_time - datetime.timedelta(days=window_days)

    due_doses = MedicationDose.objects.filter(
        medication__patient=patient_profile,
        scheduled_for__gte=start_time,
        scheduled_for__lte=ref_time
    )

    total_due = due_doses.count()
    taken_count = due_doses.filter(status="taken").count()
    missed_count = due_doses.filter(status="missed").count()
    pending_count = due_doses.filter(status="pending").count()

    adherence_pct = round((taken_count / total_due * 100), 1) if total_due > 0 else 100.0

    return {
        "total_due": total_due,
        "taken": taken_count,
        "missed": missed_count,
        "pending": pending_count,
        "adherence_percentage": adherence_pct,
        "window_days": window_days,
    }
