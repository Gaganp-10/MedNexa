from rest_framework import serializers
from .models import Alert


class AlertReadUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer strictly for updating the is_read status of an Alert.
    All other fields are read-only.
    """
    is_read = serializers.BooleanField(required=True)

    class Meta:
        model = Alert
        fields = [
            "id",
            "patient",
            "message",
            "severity",
            "is_read",
            "created_at",
        ]
        read_only_fields = ["id", "patient", "message", "severity", "created_at"]
