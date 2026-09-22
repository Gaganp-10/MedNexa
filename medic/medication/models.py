from django.db import models
from accounts.models import PatientProfile


class Medication(models.Model):
    """
    Prescription record defining a scheduled medication.
    Note: taken_status is retained as a legacy/summary field for backward compatibility.
    MedicationDose is the authoritative source of truth for daily dose tracking.
    """
    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="medications"
    )

    medicine_name = models.CharField(max_length=200)

    dosage = models.CharField(max_length=100)

    time = models.TimeField()

    taken_status = models.BooleanField(
        default=False,
        help_text="Legacy summary flag. Use related MedicationDose records for daily adherence."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.user.username} - {self.medicine_name}"


class MedicationDose(models.Model):
    """
    Individual scheduled dose instance for a prescribed medication.
    Authoritative source for daily adherence, WebSocket reminders, and missed-dose detection.
    """
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("taken", "Taken"),
        ("missed", "Missed"),
    )

    medication = models.ForeignKey(
        Medication,
        on_delete=models.CASCADE,
        related_name="doses"
    )

    scheduled_for = models.DateTimeField(
        db_index=True,
        help_text="Timezone-aware scheduled dose datetime"
    )

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="pending",
        db_index=True
    )

    taken_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Exact timestamp when the patient recorded taking this dose"
    )

    reminder_sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the ~30-min reminder was dispatched to the patient"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["medication", "scheduled_for"],
                name="unique_medication_scheduled_dose"
            )
        ]
        ordering = ["scheduled_for"]

    def __str__(self):
        return f"{self.medication.medicine_name} @ {self.scheduled_for} ({self.status})"