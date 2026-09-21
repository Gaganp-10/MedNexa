import os
import mimetypes
from django.http import Http404, FileResponse
from rest_framework import generics, serializers, status
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsPatient
from accounts.access import get_accessible_patient
from .models import DailyHealthLog, WoundImage
from .serializers import DailyHealthLogSerializer, WoundImageSerializer
from alerts.services import analyze_health_log
from .ai_analysis import analyze_wound_image
from .recovery_score import calculate_recovery_score


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
        return FileResponse(open(wound.image.path, "rb"), content_type=content_type or "image/jpeg")