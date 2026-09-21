from rest_framework import serializers
from .models import Medication


class MedicationSerializer(serializers.ModelSerializer):
    """
    Serializer for Medication records with explicit fields.
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
    Serializer for patient updating only their dose taken status.
    """
    taken_status = serializers.BooleanField(required=True)

    class Meta:
        model = Medication
        fields = ["taken_status"]