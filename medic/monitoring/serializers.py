import os
from PIL import Image as PILImage
from rest_framework import serializers
from .models import DailyHealthLog, WoundImage

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


class DailyHealthLogSerializer(serializers.ModelSerializer):
    """
    Serializer for DailyHealthLog with strict clinical input validation.
    """
    temperature = serializers.FloatField(
        min_value=35.0,
        max_value=42.0,
        help_text="Body temperature in Celsius (valid physiological range: 35.0 - 42.0)"
    )
    pain_level = serializers.IntegerField(
        min_value=0,
        max_value=10,
        help_text="Self-reported pain level from 0 (no pain) to 10 (worst pain imaginable)"
    )
    swelling = serializers.BooleanField(default=False)
    medication_taken = serializers.BooleanField(default=False)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=1000)

    class Meta:
        model = DailyHealthLog
        fields = [
            "id",
            "patient",
            "temperature",
            "pain_level",
            "swelling",
            "medication_taken",
            "notes",
            "recovery_score",
            "created_at",
        ]
        read_only_fields = ["id", "patient", "recovery_score", "created_at"]


class WoundImageSerializer(serializers.ModelSerializer):
    """
    Serializer for WoundImage uploads with strict file verification and secure streaming URL.
    """
    file_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = WoundImage
        fields = [
            "id",
            "patient",
            "image",
            "analysis_result",
            "uploaded_at",
            "file_url",
        ]
        read_only_fields = ["id", "patient", "analysis_result", "uploaded_at", "file_url"]

    def get_file_url(self, obj):
        request = self.context.get("request")
        relative_url = f"/api/wound/images/{obj.id}/file/"
        if request:
            return request.build_absolute_uri(relative_url)
        return relative_url

    def validate_image(self, file_obj):
        # 1. Size check
        if file_obj.size > MAX_IMAGE_SIZE_BYTES:
            raise serializers.ValidationError(
                f"Image file exceeds maximum allowable size of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)} MB."
            )

        # 2. Extension check
        ext = os.path.splitext(file_obj.name)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}."
            )

        # 3. Content decode check via Pillow
        try:
            image = PILImage.open(file_obj)
            image.verify()
            if image.format.upper() not in ["JPEG", "PNG"]:
                raise serializers.ValidationError(
                    f"Invalid image format '{image.format}'. Only JPEG and PNG are permitted."
                )
            # Reset pointer after verify()
            file_obj.seek(0)
        except Exception as e:
            raise serializers.ValidationError(f"Uploaded file is corrupted or not a valid image: {e}")

        return file_obj