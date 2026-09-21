from django.db import models
from accounts.models import PatientProfile


class Medication(models.Model):

    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="medications"
    )

    medicine_name = models.CharField(max_length=200)

    dosage = models.CharField(max_length=100)

    time = models.TimeField()

    taken_status = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.user.username} - {self.medicine_name}"