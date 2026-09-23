from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.openapi import OpenApiTypes
from .models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.IntegerField(source="sender.id", read_only=True)
    sender_name = serializers.SerializerMethodField()
    sender_role = serializers.CharField(source="sender.role", read_only=True)
    content = serializers.CharField(
        max_length=4000,
        required=True,
        allow_blank=False,
        trim_whitespace=True
    )

    class Meta:
        model = Message
        fields = [
            "id",
            "conversation_id",
            "sender_id",
            "sender_name",
            "sender_role",
            "content",
            "is_read",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "conversation_id",
            "sender_id",
            "sender_name",
            "sender_role",
            "is_read",
            "created_at",
        ]

    @extend_schema_field(OpenApiTypes.STR)
    def get_sender_name(self, obj):
        return obj.sender.get_full_name() or obj.sender.username

    def validate_content(self, value):
        stripped = value.strip() if value else ""
        if not stripped:
            raise serializers.ValidationError("Message content cannot be empty or whitespace only.")
        return stripped


class ConversationSerializer(serializers.ModelSerializer):
    doctor_id = serializers.IntegerField(source="doctor.id", read_only=True)
    doctor_name = serializers.SerializerMethodField()
    patient_id = serializers.IntegerField(source="patient.id", read_only=True)
    patient_name = serializers.SerializerMethodField()
    patient_surgery_type = serializers.CharField(source="patient.surgery_type", read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "doctor_id",
            "doctor_name",
            "patient_id",
            "patient_name",
            "patient_surgery_type",
            "last_message",
            "unread_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.STR)
    def get_doctor_name(self, obj):
        return obj.doctor.get_full_name() or obj.doctor.username

    @extend_schema_field(OpenApiTypes.STR)
    def get_patient_name(self, obj):
        return obj.patient.user.get_full_name() or obj.patient.user.username

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_last_message(self, obj):
        latest = obj.messages.order_by("-created_at").first()
        if not latest:
            return None
        return {
            "id": latest.id,
            "sender_id": latest.sender_id,
            "sender_name": latest.sender.get_full_name() or latest.sender.username,
            "content": latest.content[:100],
            "is_read": latest.is_read,
            "created_at": latest.created_at.isoformat(),
        }

    @extend_schema_field(OpenApiTypes.INT)
    def get_unread_count(self, obj):
        request = self.context.get("request")
        if not request or not request.user or not request.user.is_authenticated:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()
