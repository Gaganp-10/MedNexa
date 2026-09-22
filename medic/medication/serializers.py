from rest_framework import serializers
from .models import Medication, MedicationDose


class MedicationDoseSerializer(serializers.ModelSerializer):
    """
    Serializer for individual scheduled medication doses.
    Includes medication name and dosage for convenient frontend display.
    """
    medication_id = serializers.IntegerField(source="medication.id", read_only=True)
    medicine_name = serializers.CharField(source="medication.medicine_name", read_only=True)
    dosage = serializers.CharField(source="medication.dosage", read_only=True)

    class Meta:
        model = MedicationDose
        fields = [
            "id",
            "medication_id",
            "medicine_name",
            "dosage",
            "scheduled_for",
            "status",
            "taken_at",
            "reminder_sent_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "medication_id",
            "medicine_name",
            "dosage",
            "scheduled_for",
            "reminder_sent_at",
            "created_at",
        ]


class MedicationSerializer(serializers.ModelSerializer):
    """
    Serializer for Medication records with explicit fields.
    Note: taken_status is kept for backward compatibility with legacy consumers.
    """
    patient_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Medication
        fields = [
            "id",
            "patient",
            "patient_id",
            "medicine_name",
            "dosage",
            "time",
            "taken_status",
            "created_at",
        ]
        read_only_fields = ["id", "patient", "created_at"]


class MedicationStatusUpdateSerializer(serializers.ModelSerializer):
    """
    Legacy serializer for patient updating taken_status on the medication level.
    """
    taken_status = serializers.BooleanField(required=True)

    class Meta:
        model = Medication
        fields = ["taken_status"]