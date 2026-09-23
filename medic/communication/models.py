from django.db import models
from django.core.validators import MaxLengthValidator
from accounts.models import User, PatientProfile


class Conversation(models.Model):
    """
    Represents a 1-to-1 conversation channel between an assigned doctor and patient.
    Enforces a unique constraint so there is at most one conversation per doctor-patient pair.
    """
    doctor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="doctor_conversations",
        limit_choices_to={"role": "doctor"}
    )
    patient = models.ForeignKey(
        PatientProfile,
        on_delete=models.CASCADE,
        related_name="conversations"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "patient"],
                name="unique_doctor_patient_conversation"
            )
        ]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Conversation(doctor={self.doctor.username}, patient={self.patient.user.username})"


class Message(models.Model):
    """
    Individual message sent within a conversation.
    Sender is strictly authenticated User.
    Content is non-blank and capped at 4,000 characters.
    created_at is indexed for fast chronological queries.
    """
    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="sent_messages"
    )
    content = models.TextField(
        validators=[MaxLengthValidator(4000)],
        blank=False
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message({self.id} from {self.sender.username} at {self.created_at})"
