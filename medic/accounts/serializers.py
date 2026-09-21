from rest_framework import serializers
from .models import PatientProfile


class PatientProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for PatientProfile with explicit fields.
    """
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)
    doctor_id = serializers.IntegerField(source="doctor.id", read_only=True, allow_null=True)

    class Meta:
        model = PatientProfile
        fields = [
            "id",
            "user_id",
            "username",
            "surgery_type",
            "surgery_date",
            "doctor_id",
        ]
        read_only_fields = ["id", "user_id", "username", "doctor_id"]