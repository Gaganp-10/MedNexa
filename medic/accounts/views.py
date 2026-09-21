from django.http import Http404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from .models import PatientProfile
from .serializers import PatientProfileSerializer
from .permissions import IsDoctor
from .access import get_accessible_patient
from monitoring.models import DailyHealthLog, WoundImage
from monitoring.serializers import DailyHealthLogSerializer, WoundImageSerializer
from monitoring.risk_prediction import predict_patient_risk
from alerts.models import Alert
from medication.models import Medication


class DoctorPatientsView(generics.ListAPIView):
    """
    Returns list of patients assigned to the calling authenticated doctor.
    """
    permission_classes = [IsAuthenticated, IsDoctor]
    serializer_class = PatientProfileSerializer

    def get_queryset(self):
        return PatientProfile.objects.filter(
            doctor=self.request.user
        ).select_related("user", "doctor").order_by("id")


class DoctorOverviewView(APIView):
    """
    Returns a comprehensive post-surgery overview for the authenticated doctor.
    Derives doctor identity from request.user.
    Uses select_related and prefetch_related to eliminate N+1 queries.
    Handles empty patient states gracefully.
    """
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        doctor = request.user
        patients = (
            PatientProfile.objects.filter(doctor=doctor)
            .select_related("user")
            .prefetch_related("health_logs", "wound_images", "alerts", "medications")
            .order_by("id")
        )

        patient_summaries = []

        for p in patients:
            # Prefetched querysets
            logs = list(p.health_logs.all())
            wounds = list(p.wound_images.all())
            alerts = list(p.alerts.all())
            meds = list(p.medications.all())

            latest_log = logs[0] if logs else None
            latest_wound = wounds[0] if wounds else None

            # Calculate risk and recovery
            wound_res = latest_wound.analysis_result if latest_wound else ""
            risk_indicator = predict_patient_risk(latest_log, wound_res)
            latest_recovery_score = latest_log.recovery_score if latest_log else 100

            # Medication adherence
            total_meds = len(meds)
            taken_meds = sum(1 for m in meds if m.taken_status)
            adherence_pct = round((taken_meds / total_meds * 100), 1) if total_meds > 0 else 100.0

            log_summary = None
            if latest_log:
                log_summary = {
                    "id": latest_log.id,
                    "created_at": latest_log.created_at,
                    "temperature": latest_log.temperature,
                    "pain_level": latest_log.pain_level,
                    "swelling": latest_log.swelling,
                    "recovery_score": latest_log.recovery_score,
                }

            wound_summary = None
            if latest_wound:
                wound_summary = {
                    "id": latest_wound.id,
                    "uploaded_at": latest_wound.uploaded_at,
                    "analysis_result": latest_wound.analysis_result,
                    "file_url": f"/api/wound/images/{latest_wound.id}/file/",
                }

            patient_summaries.append({
                "patient_id": p.id,
                "user_id": p.user.id,
                "username": p.user.username,
                "full_name": p.user.get_full_name() or p.user.username,
                "surgery_type": p.surgery_type,
                "surgery_date": str(p.surgery_date),
                "latest_recovery_score": latest_recovery_score,
                "latest_risk_indicator": risk_indicator,
                "alert_count": len(alerts),
                "latest_health_log": log_summary,
                "latest_wound_upload": wound_summary,
                "medication_adherence": {
                    "total_prescribed": total_meds,
                    "doses_recorded_taken": taken_meds,
                    "adherence_percentage": adherence_pct,
                },
            })

        return Response({
            "doctor_id": doctor.id,
            "doctor_name": doctor.get_full_name() or doctor.username,
            "total_patients": len(patient_summaries),
            "patients": patient_summaries,
        })


class PatientHealthLogsView(generics.ListAPIView):
    """
    Returns health logs for a specific patient.
    Accessible only to the patient themselves, their assigned doctor, or superusers.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = DailyHealthLogSerializer

    def get_queryset(self):
        patient_id = self.kwargs["patient_id"]
        patient = get_accessible_patient(self.request.user, patient_id)
        return DailyHealthLog.objects.filter(patient=patient).select_related("patient__user").order_by("-created_at")


class PatientWoundImagesView(generics.ListAPIView):
    """
    Returns wound image records for a specific patient.
    Accessible only to the patient themselves, their assigned doctor, or superusers.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = WoundImageSerializer

    def get_queryset(self):
        patient_id = self.kwargs["patient_id"]
        patient = get_accessible_patient(self.request.user, patient_id)
        return WoundImage.objects.filter(patient=patient).select_related("patient__user").order_by("-uploaded_at")


class PatientAlertsView(APIView):
    """
    Returns alerts for a specific patient.
    Accessible only to the patient themselves, their assigned doctor, or superusers.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        patient = get_accessible_patient(request.user, patient_id)
        alerts = Alert.objects.filter(patient=patient).order_by("-created_at")

        data = [
            {
                "id": alert.id,
                "message": alert.message,
                "severity": alert.severity,
                "created_at": alert.created_at,
            }
            for alert in alerts
        ]
        return Response(data)


class PatientRecoveryTrendView(APIView):
    """
    Returns the historical recovery scores for a specific patient.
    Accessible only to the patient themselves, their assigned doctor, or superusers.
    Handles empty state without error.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        patient = get_accessible_patient(request.user, patient_id)
        logs = DailyHealthLog.objects.filter(patient=patient).order_by("created_at")

        data = [
            {
                "date": log.created_at.date(),
                "score": log.recovery_score,
            }
            for log in logs
        ]
        return Response(data)


class PatientRiskPredictionView(APIView):
    """
    Returns current prototype risk assessment indicator for a specific patient.
    Accessible only to the patient themselves, their assigned doctor, or superusers.
    Handles empty state gracefully.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        patient = get_accessible_patient(request.user, patient_id)

        latest_log = DailyHealthLog.objects.filter(patient=patient).order_by("-created_at").first()
        latest_wound = WoundImage.objects.filter(patient=patient).order_by("-uploaded_at").first()

        wound_result = latest_wound.analysis_result if latest_wound else ""
        risk = predict_patient_risk(latest_log, wound_result)

        return Response({
            "patient_id": patient.id,
            "risk_prediction": risk,
            "has_health_logs": latest_log is not None,
            "has_wound_images": latest_wound is not None,
        })