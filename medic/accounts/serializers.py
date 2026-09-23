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


class AssignedDoctorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class AuthMeResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()
    patient_profile_id = serializers.IntegerField(required=False, allow_null=True)
    doctor_profile_id = serializers.IntegerField(required=False, allow_null=True)
    assigned_doctor = AssignedDoctorSerializer(required=False, allow_null=True)


class PatientProfileMeResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    role = serializers.CharField()
    patient_profile_id = serializers.IntegerField()
    surgery_type = serializers.CharField()
    surgery_date = serializers.CharField()
    assigned_doctor = AssignedDoctorSerializer(required=False, allow_null=True)


class RiskPredictionResponseSerializer(serializers.Serializer):
    patient_id = serializers.IntegerField(help_text="PatientProfile.id")
    risk_prediction = serializers.CharField(help_text="Prototype heuristic risk assessment: low, medium, or high")
    has_health_logs = serializers.BooleanField()
    has_wound_images = serializers.BooleanField()


class RecoveryTrendItemSerializer(serializers.Serializer):
    date = serializers.DateField()
    score = serializers.IntegerField(help_text="Computed recovery score (0-100)")


class PatientAlertSummarySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    message = serializers.CharField()
    severity = serializers.CharField()
    created_at = serializers.DateTimeField()