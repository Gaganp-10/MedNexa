from django.db import models
from accounts.models import PatientProfile


class Alert(models.Model):

    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="alerts"
    )

    message = models.TextField()

    severity = models.CharField(
        max_length=20,
        choices=[
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High")
        ]
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.user.username} - {self.severity}"