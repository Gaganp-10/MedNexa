import datetime
from django.utils import timezone
from django.http import Http404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes, OpenApiResponse

from .models import PatientProfile
from .serializers import (
    PatientProfileSerializer,
    AuthMeResponseSerializer,
    PatientProfileMeResponseSerializer,
    RiskPredictionResponseSerializer,
    RecoveryTrendItemSerializer,
    PatientAlertSummarySerializer,
)
from .permissions import IsDoctor
from .access import get_accessible_patient
from monitoring.models import DailyHealthLog, WoundImage
from monitoring.serializers import DailyHealthLogSerializer, WoundImageSerializer
from monitoring.risk_prediction import predict_patient_risk
from alerts.models import Alert
from medication.models import Medication


@extend_schema(
    summary="List Assigned Patients",
    description="Returns list of patients currently assigned to the calling authenticated doctor.",
    responses={
        200: PatientProfileSerializer(many=True),
        401: OpenApiResponse(description="Unauthenticated"),
        403: OpenApiResponse(description="Caller is not a doctor"),
    }
)
class DoctorPatientsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsDoctor]
    serializer_class = PatientProfileSerializer

    def get_queryset(self):
        return PatientProfile.objects.filter(
            doctor=self.request.user
        ).select_related("user", "doctor").order_by("id")


@extend_schema(
    summary="Doctor Dashboard Overview",
    description=(
        "Returns a comprehensive post-surgery overview for the authenticated doctor. "
        "Includes each assigned patient's latest vitals, wound analysis results, "
        "prototype risk predictions, and 7-day medication adherence metrics. "
        "Outputs are prototype decision-support indicators, not diagnostic findings."
    ),
    responses={
        200: OpenApiResponse(
            description="Comprehensive doctor overview with patient summaries"
        ),
        401: OpenApiResponse(description="Unauthenticated"),
        403: OpenApiResponse(description="Caller is not a doctor"),
    }
)
class DoctorOverviewView(APIView):
    permission_classes = [IsAuthenticated, IsDoctor]

    def get(self, request):
        doctor = request.user
        patients = (
            PatientProfile.objects.filter(doctor=doctor)
            .select_related("user")
            .prefetch_related("health_logs", "wound_images", "alerts", "medications__doses")
            .order_by("id")
        )

        patient_summaries = []
        now = timezone.now()
        window_start = now - datetime.timedelta(days=7)

        for p in patients:
            logs = list(p.health_logs.all())
            wounds = list(p.wound_images.all())
            alerts = list(p.alerts.all())
            meds = list(p.medications.all())

            latest_log = logs[0] if logs else None
            latest_wound = wounds[0] if wounds else None

            wound_res = latest_wound.analysis_result if latest_wound else ""
            risk_indicator = predict_patient_risk(latest_log, wound_res)
            latest_recovery_score = latest_log.recovery_score if latest_log else 100

            all_doses = [d for m in meds for d in m.doses.all()]
            due_doses = [d for d in all_doses if d.scheduled_for >= window_start and d.scheduled_for <= now]

            total_due = len(due_doses)
            taken_doses = sum(1 for d in due_doses if d.status == "taken")
            missed_doses = sum(1 for d in due_doses if d.status == "missed")
            adherence_pct = round((taken_doses / total_due * 100), 1) if total_due > 0 else 100.0

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
                    "total_prescribed": len(meds),
                    "total_scheduled_due": total_due,
                    "doses_taken": taken_doses,
                    "doses_missed": missed_doses,
                    "doses_recorded_taken": taken_doses,
                    "adherence_percentage": adherence_pct,
                },
            })

        return Response({
            "doctor_id": doctor.id,
            "doctor_name": doctor.get_full_name() or doctor.username,
            "total_patients": len(patient_summaries),
            "patients": patient_summaries,
        })


@extend_schema(
    summary="Get Patient Health Logs",
    description=(
        "Returns health logs for a specific patient. "
        "Accessible only to the patient themselves, their currently assigned doctor, or an admin. "
        "Returns 404 (not 403) for any other caller to prevent existence enumeration."
    ),
    parameters=[
        OpenApiParameter(
            name="patient_id",
            type=int,
            location=OpenApiParameter.PATH,
            description="PatientProfile.id (primary key of PatientProfile). Enforces ownership/assignment."
        )
    ],
    responses={
        200: DailyHealthLogSerializer(many=True),
        404: OpenApiResponse(description="Patient not found or unauthorized"),
    }
)
class PatientHealthLogsView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = DailyHealthLogSerializer

    def get_queryset(self):
        patient_id = self.kwargs["patient_id"]
        patient = get_accessible_patient(self.request.user, patient_id)
        return DailyHealthLog.objects.filter(patient=patient).select_related("patient__user").order_by("-created_at")


@extend_schema(
    summary="Get Patient Wound Images",
    description=(
        "Returns metadata and file URLs for wound images belonging to a specific patient. "
        "Accessible only to the patient themselves, their currently assigned doctor, or an admin. "
        "Returns 404 (not 403) for any other caller to prevent existence enumeration."
    ),
    parameters=[
        OpenApiParameter(
            name="patient_id",
            type=int,
            location=OpenApiParameter.PATH,
            description="PatientProfile.id (primary key of PatientProfile). Enforces ownership/assignment."
        )
    ],
    responses={
        200: WoundImageSerializer(many=True),
        404: OpenApiResponse(description="Patient not found or unauthorized"),
    }
)
class PatientWoundImagesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = WoundImageSerializer

    def get_queryset(self):
        patient_id = self.kwargs["patient_id"]
        patient = get_accessible_patient(self.request.user, patient_id)
        return WoundImage.objects.filter(patient=patient).select_related("patient__user").order_by("-uploaded_at")


@extend_schema(
    summary="Get Patient Alerts",
    description=(
        "Returns system alerts generated for a specific patient. "
        "Accessible only to the patient themselves, their currently assigned doctor, or an admin. "
        "Returns 404 (not 403) for any other caller to prevent existence enumeration."
    ),
    parameters=[
        OpenApiParameter(
            name="patient_id",
            type=int,
            location=OpenApiParameter.PATH,
            description="PatientProfile.id (primary key of PatientProfile). Enforces ownership/assignment."
        )
    ],
    responses={
        200: PatientAlertSummarySerializer(many=True),
        404: OpenApiResponse(description="Patient not found or unauthorized"),
    }
)
class PatientAlertsView(APIView):
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


@extend_schema(
    summary="Get Patient Recovery Trend",
    description=(
        "Returns chronological recovery scores for a specific patient over time. "
        "Accessible only to the patient themselves, their currently assigned doctor, or an admin. "
        "Returns 404 (not 403) for any other caller to prevent existence enumeration."
    ),
    parameters=[
        OpenApiParameter(
            name="patient_id",
            type=int,
            location=OpenApiParameter.PATH,
            description="PatientProfile.id (primary key of PatientProfile). Enforces ownership/assignment."
        )
    ],
    responses={
        200: RecoveryTrendItemSerializer(many=True),
        404: OpenApiResponse(description="Patient not found or unauthorized"),
    }
)
class PatientRecoveryTrendView(APIView):
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


@extend_schema(
    summary="Get Patient Risk Prediction",
    description=(
        "Returns prototype clinical decision-support risk indicator for a specific patient. "
        "MEDICAL SAFETY NOTICE: This is a prototype decision-support heuristic, NOT a diagnostic finding. "
        "Accessible only to the patient themselves, their currently assigned doctor, or an admin. "
        "Returns 404 (not 403) for any other caller to prevent existence enumeration."
    ),
    parameters=[
        OpenApiParameter(
            name="patient_id",
            type=int,
            location=OpenApiParameter.PATH,
            description="PatientProfile.id (primary key of PatientProfile). Enforces ownership/assignment."
        )
    ],
    responses={
        200: RiskPredictionResponseSerializer,
        404: OpenApiResponse(description="Patient not found or unauthorized"),
    }
)
class PatientRiskPredictionView(APIView):
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


@extend_schema(
    summary="Get Current User Profile & Role Metadata",
    description=(
        "Returns identity and role profile metadata for the authenticated caller.\n"
        "- Common fields: id, username, role ('doctor' or 'patient')\n"
        "- For patients: patient_profile_id and assigned_doctor (id, name)\n"
        "- For doctors: doctor_profile_id"
    ),
    responses={
        200: AuthMeResponseSerializer,
        401: OpenApiResponse(description="Unauthenticated"),
    }
)
class AuthMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        data = {
            "id": user.id,
            "username": user.username,
            "role": user.role,
        }

        if user.role == "patient":
            patient_profile = getattr(user, "patientprofile", None)
            data["patient_profile_id"] = patient_profile.id if patient_profile else None
            if patient_profile and patient_profile.doctor:
                doc = patient_profile.doctor
                data["assigned_doctor"] = {
                    "id": doc.id,
                    "name": doc.get_full_name() or doc.username,
                }
            else:
                data["assigned_doctor"] = None
        elif user.role == "doctor":
            doctor_profile = getattr(user, "doctorprofile", None)
            data["doctor_profile_id"] = doctor_profile.id if doctor_profile else None

        return Response(data)


@extend_schema(
    summary="Get Patient Profile (Self)",
    description="Convenience endpoint for authenticated patients to retrieve their own post-surgery profile and assigned doctor.",
    responses={
        200: PatientProfileMeResponseSerializer,
        401: OpenApiResponse(description="Unauthenticated"),
        403: OpenApiResponse(description="Caller is not a patient"),
        404: OpenApiResponse(description="Patient profile not found"),
    }
)
class PatientProfileMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != "patient":
            return Response(
                {"detail": "Only patient accounts can access this profile endpoint."},
                status=403
            )

        patient_profile = getattr(request.user, "patientprofile", None)
        if not patient_profile:
            return Response(
                {"detail": "Patient profile not found."},
                status=404
            )

        doctor_info = None
        if patient_profile.doctor:
            doc = patient_profile.doctor
            doctor_info = {
                "id": doc.id,
                "name": doc.get_full_name() or doc.username,
            }

        return Response({
            "id": request.user.id,
            "username": request.user.username,
            "role": request.user.role,
            "patient_profile_id": patient_profile.id,
            "surgery_type": patient_profile.surgery_type,
            "surgery_date": str(patient_profile.surgery_date),
            "assigned_doctor": doctor_info,
        })