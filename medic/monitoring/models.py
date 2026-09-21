import os
import uuid
from django.db import models
from accounts.models import PatientProfile


def wound_image_upload_path(instance, filename):
    """
    Generates a secure, randomized UUID filename to prevent directory traversal
    and filename enumeration attacks.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        ext = ".jpg"
    return f"wound_images/{uuid.uuid4().hex}{ext}"


class DailyHealthLog(models.Model):

    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="health_logs"
    )

    temperature = models.FloatField()

    pain_level = models.IntegerField()

    swelling = models.BooleanField(default=False)

    medication_taken = models.BooleanField(default=False)

    notes = models.TextField(blank=True)

    recovery_score = models.IntegerField(default=100)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.patient.user.username} - {self.created_at}"


class WoundImage(models.Model):

    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="wound_images"
    )

    image = models.ImageField(upload_to=wound_image_upload_path)

    analysis_result = models.TextField(blank=True)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return f"Wound Image - {self.patient.user.username}"
