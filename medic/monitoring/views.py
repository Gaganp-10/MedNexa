import os
import mimetypes
from django.http import Http404, FileResponse
from rest_framework import generics, serializers, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse
from drf_spectacular.openapi import OpenApiTypes

from accounts.permissions import IsPatient
from accounts.access import get_accessible_patient
from .models import DailyHealthLog, WoundImage
from .serializers import DailyHealthLogSerializer, WoundImageSerializer
from alerts.services import analyze_health_log
from .ai_analysis import analyze_wound_image
from .recovery_score import calculate_recovery_score


@extend_schema(
    summary="Submit Daily Health Log",
    description=(
        "Creates a new daily health log for the authenticated patient. "
        "Patient identity is derived server-side from request.user — "
        "no patient_id is accepted in the body. "
        "Automatically computes a prototype recovery score and triggers "
        "decision-support alert analysis on submission."
    ),
    request=DailyHealthLogSerializer,
    responses={
        201: DailyHealthLogSerializer,
        400: OpenApiResponse(description="Validation error"),
        403: OpenApiResponse(description="Caller is not a patient"),
    }
)
class CreateHealthLogView(generics.CreateAPIView):
    """
    Creates a new daily health log for the authenticated patient.
    Derives patient identity from request.user's PatientProfile.
    """
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class = DailyHealthLogSerializer

    def perform_create(self, serializer):
        patient_profile = getattr(self.request.user, "patientprofile", None)
        if not patient_profile:
            raise serializers.ValidationError({"detail": "No patient profile associated with this account."})

        # Save with explicitly derived patient, ignoring any client-provided patient ID
        log = serializer.save(patient=patient_profile)

        # Retrieve latest wound analysis for recovery score heuristic
        wound_result = ""
        latest_wound = WoundImage.objects.filter(patient=patient_profile).order_by("-uploaded_at").first()
        if latest_wound:
            wound_result = latest_wound.analysis_result

        score = calculate_recovery_score(log, wound_result)
        log.recovery_score = score
        log.save()

        # Trigger decision-support alert analysis
        analyze_health_log(log)


@extend_schema(
    summary="List Own Health Logs",
    description=(
        "Lists all health logs for the authenticated patient, paginated, newest first. "
        "Restricted to patients only; doctors access patient logs via "
        "GET /api/patient/<patient_id>/logs/."
    ),
    responses={
        200: DailyHealthLogSerializer(many=True),
        403: OpenApiResponse(description="Caller is not a patient"),
    }
)
class HealthLogListView(generics.ListAPIView):
    """
    Lists health logs belonging strictly to the calling authenticated patient.
    Paginated automatically via REST_FRAMEWORK settings.
    """
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class = DailyHealthLogSerializer

    def get_queryset(self):
        patient_profile = getattr(self.request.user, "patientprofile", None)
        if not patient_profile:
            return DailyHealthLog.objects.none()

        return DailyHealthLog.objects.filter(
            patient=patient_profile
        ).select_related("patient__user").order_by("-created_at")


@extend_schema(
    summary="Upload Wound Image",
    description=(
        "Uploads a wound image for the authenticated patient. "
        "Request must use `multipart/form-data` with the file field named `image`. "
        "Patient identity is derived server-side. "
        "Runs a prototype OpenCV image analysis heuristic automatically after upload. "
        "MEDICAL SAFETY NOTICE: Image analysis results are prototype decision-support indicators, "
        "not clinically validated diagnostic findings."
    ),
    request={
        "multipart/form-data": WoundImageSerializer,
    },
    responses={
        201: WoundImageSerializer,
        400: OpenApiResponse(description="Missing or invalid image file"),
        403: OpenApiResponse(description="Caller is not a patient"),
    }
)
class UploadWoundImageView(generics.CreateAPIView):
    """
    Uploads a wound image for the authenticated patient.
    Derives patient identity from request.user's PatientProfile.
    Runs prototype image analysis heuristic upon upload.
    """
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class = WoundImageSerializer

    def perform_create(self, serializer):
        patient_profile = getattr(self.request.user, "patientprofile", None)
        if not patient_profile:
            raise serializers.ValidationError({"detail": "No patient profile associated with this account."})

        wound = serializer.save(patient=patient_profile)

        # Run prototype OpenCV analysis heuristic
        try:
            result = analyze_wound_image(wound.image.path)
        except Exception:
            result = "Image analysis error; manual medical review recommended (prototype indicator)"

        wound.analysis_result = result
        wound.save()


@extend_schema(
    summary="List Own Wound Images",
    description=(
        "Lists wound image records for the authenticated patient, paginated, newest first. "
        "Restricted to patients only; doctors access wound images via "
        "GET /api/patient/<patient_id>/wounds/."
    ),
    responses={
        200: WoundImageSerializer(many=True),
        403: OpenApiResponse(description="Caller is not a patient"),
    }
)
class WoundImageListView(generics.ListAPIView):
    """
    Lists wound images belonging strictly to the calling authenticated patient.
    Paginated automatically via REST_FRAMEWORK settings.
    """
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class = WoundImageSerializer

    def get_queryset(self):
        patient_profile = getattr(self.request.user, "patientprofile", None)
        if not patient_profile:
            return WoundImage.objects.none()

        return WoundImage.objects.filter(
            patient=patient_profile
        ).select_related("patient__user").order_by("-uploaded_at")


@extend_schema(
    summary="Stream Wound Image File",
    description=(
        "Securely streams the raw wound image file binary after validating ownership. "
        "Access is restricted to the patient themselves, their currently assigned doctor, or an admin. "
        "Returns 404 (not 403) for unauthorized access to prevent existence enumeration. "
        "Response is the raw image binary, not JSON. "
        "Use this URL from `file_url` in the WoundImage metadata response."
    ),
    parameters=[
        OpenApiParameter(
            name="image_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="WoundImage primary key"
        )
    ],
    responses={
        200: OpenApiResponse(description="Raw image binary (image/jpeg or image/png)"),
        404: OpenApiResponse(description="Image not found or unauthorized"),
    }
)
class WoundImageFileStreamView(APIView):
    """
    Securely streams a wound image file after checking object-level permissions.
    Only the patient themselves, their assigned doctor, or a superuser can access.
    Returns HTTP 404 for unauthorized requests to prevent existence enumeration.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, image_id):
        try:
            wound = WoundImage.objects.select_related("patient__user", "patient__doctor").get(pk=image_id)
        except WoundImage.DoesNotExist:
            raise Http404("Image not found.")

        # Enforce authorization via central access helper
        get_accessible_patient(request.user, wound.patient_id)

        if not wound.image or not os.path.exists(wound.image.path):
            raise Http404("Image file not found on disk.")

        content_type, _ = mimetypes.guess_type(wound.image.path)
        response = FileResponse(open(wound.image.path, "rb"), content_type=content_type or "image/jpeg")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response