import datetime
from django.http import Http404
from django.utils import timezone
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes

from accounts.permissions import IsDoctor, IsPatient
from accounts.access import get_accessible_patient
from .models import Medication, MedicationDose
from .serializers import (
    MedicationSerializer,
    MedicationStatusUpdateSerializer,
    MedicationDoseSerializer,
)
from .services import generate_upcoming_doses, calculate_patient_adherence


@extend_schema(
    summary="Prescribe Medication (Doctor)",
    description=(
        "Allows a doctor to prescribe medication for their assigned patient. "
        "Validates assignment using get_accessible_patient. "
        "Immediately generates upcoming doses for the next 7 days."
    ),
    request=MedicationSerializer,
    responses={
        201: MedicationSerializer,
        400: OpenApiResponse(description="Missing patient_id or invalid fields"),
        404: OpenApiResponse(description="Patient not found or not assigned to this doctor"),
    }
)
class CreateMedicationView(generics.CreateAPIView):
    """
    Allows a doctor to prescribe medication for their assigned patients.
    Validates assignment using get_accessible_patient.
    Immediately generates upcoming doses for the newly prescribed medication.
    """
    permission_classes = [IsAuthenticated, IsDoctor]
    serializer_class = MedicationSerializer

    def perform_create(self, serializer):
        patient_id = self.request.data.get("patient_id")
        if not patient_id:
            raise serializers.ValidationError({"patient_id": "patient_id is required."})

        # Verify that the patient exists and is assigned to this doctor (or superuser)
        patient_profile = get_accessible_patient(self.request.user, patient_id)

        if not self.request.user.is_superuser and patient_profile.doctor_id != self.request.user.id:
            raise Http404("Patient not found or not assigned to you.")

        medication = serializer.save(patient=patient_profile)

        # Generate upcoming doses immediately
        generate_upcoming_doses(medication, days=7)


@extend_schema(
    summary="List Patient Medications",
    description=(
        "Lists all medications prescribed for a specific patient. "
        "Accessible to the patient themselves, their assigned doctor, or an admin. "
        "Returns 404 for unauthorized access to prevent existence enumeration."
    ),
    parameters=[
        OpenApiParameter(
            name="patient_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="PatientProfile.id (primary key of PatientProfile)"
        )
    ],
    responses={
        200: MedicationSerializer(many=True),
        404: OpenApiResponse(description="Patient not found or unauthorized"),
    }
)
class MedicationListView(generics.ListAPIView):
    """
    Lists medications for a specific patient.
    Accessible only to the patient themselves, their assigned doctor, or superusers.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MedicationSerializer

    def get_queryset(self):
        patient_id = self.kwargs["patient_id"]
        # Enforce authorization boundary
        patient_profile = get_accessible_patient(self.request.user, patient_id)
        return Medication.objects.filter(patient=patient_profile).order_by("-created_at")


@extend_schema(
    summary="Update Medication Taken Status (Legacy)",
    description=(
        "Legacy endpoint for a patient to mark a medication prescription as taken. "
        "Synchronizes today's dose record to 'taken'. "
        "For per-dose recording, prefer PATCH /api/medication/doses/<dose_id>/take/."
    ),
    parameters=[
        OpenApiParameter(
            name="medication_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Medication primary key"
        )
    ],
    request=MedicationStatusUpdateSerializer,
    responses={
        200: MedicationSerializer,
        403: OpenApiResponse(description="Caller is not a patient"),
        404: OpenApiResponse(description="Medication not found or not owned by caller"),
    }
)
class MedicationStatusUpdateView(generics.UpdateAPIView):
    """
    Legacy endpoint for patient updating taken_status of their own prescribed medication.
    Synchronizes the active dose for today to 'taken'.
    """
    permission_classes = [IsAuthenticated, IsPatient]
    serializer_class = MedicationStatusUpdateSerializer
    http_method_names = ["patch"]

    def get_object(self):
        medication_id = self.kwargs.get("medication_id")
        try:
            medication = Medication.objects.select_related("patient__user").get(pk=medication_id)
        except Medication.DoesNotExist:
            raise Http404("Medication not found.")

        # Ensure the calling patient owns this medication
        if medication.patient.user_id != self.request.user.id:
            raise Http404("Medication not found.")

        return medication

    def patch(self, request, *args, **kwargs):
        medication = self.get_object()
        serializer = self.get_serializer(medication, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Synchronize today's dose if marking as taken
        if serializer.validated_data.get("taken_status"):
            today = timezone.localdate()
            today_dose = MedicationDose.objects.filter(
                medication=medication,
                scheduled_for__date=today
            ).first()

            if not today_dose:
                # If no dose exists for today yet, generate it
                doses = generate_upcoming_doses(medication, days=1, start_date=today)
                today_dose = doses[0] if doses else None

            if today_dose and today_dose.status != "taken":
                today_dose.status = "taken"
                today_dose.taken_at = timezone.now()
                today_dose.save(update_fields=["status", "taken_at"])

        return Response(MedicationSerializer(medication).data)


@extend_schema(
    summary="Get Today's Scheduled Doses",
    description=(
        "Returns all medication doses scheduled for today (00:00–23:59 local time) "
        "for the authenticated patient. Patient identity derived from request.user."
    ),
    responses={
        200: MedicationDoseSerializer(many=True),
        403: OpenApiResponse(description="Caller is not a patient"),
    }
)
class PatientTodayDosesView(APIView):
    """
    Returns all medication doses scheduled for today for the authenticated patient.
    Derives patient identity strictly from request.user.
    """
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        patient_profile = getattr(request.user, "patientprofile", None)
        if not patient_profile:
            return Response([], status=status.HTTP_200_OK)

        today = timezone.localdate()
        doses = MedicationDose.objects.filter(
            medication__patient=patient_profile,
            scheduled_for__date=today
        ).select_related("medication").order_by("scheduled_for")

        serializer = MedicationDoseSerializer(doses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get Upcoming Scheduled Doses",
    description=(
        "Returns upcoming scheduled doses for the authenticated patient. "
        "Optional `days` query parameter (default: 7) controls the look-ahead window. "
        "Patient identity derived from request.user — no patient ID required."
    ),
    parameters=[
        OpenApiParameter(
            name="days",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Look-ahead window in days (default: 7)",
            required=False,
        )
    ],
    responses={
        200: MedicationDoseSerializer(many=True),
        403: OpenApiResponse(description="Caller is not a patient"),
    }
)
class PatientUpcomingDosesView(APIView):
    """
    Returns upcoming scheduled doses for the authenticated patient.
    Derives patient identity strictly from request.user (never from query or body).
    """
    permission_classes = [IsAuthenticated, IsPatient]

    def get(self, request):
        patient_profile = getattr(request.user, "patientprofile", None)
        if not patient_profile:
            return Response([], status=status.HTTP_200_OK)

        try:
            days = int(request.query_params.get("days", 7))
        except (ValueError, TypeError):
            days = 7

        now = timezone.now()
        end_time = now + datetime.timedelta(days=days)

        doses = MedicationDose.objects.filter(
            medication__patient=patient_profile,
            scheduled_for__gte=now,
            scheduled_for__lte=end_time
        ).select_related("medication").order_by("scheduled_for")

        serializer = MedicationDoseSerializer(doses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Mark Dose as Taken",
    description=(
        "Marks a specific scheduled medication dose as taken. "
        "Restricted to patients only. Patient must own this dose. "
        "Returns 403 if caller is a doctor; 404 if dose not found or not owned."
    ),
    parameters=[
        OpenApiParameter(
            name="dose_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="MedicationDose primary key"
        )
    ],
    responses={
        200: MedicationDoseSerializer,
        403: OpenApiResponse(description="Caller is a doctor (not allowed)"),
        404: OpenApiResponse(description="Dose not found or not owned by caller"),
    }
)
class TakeDoseView(APIView):
    """
    Marks a scheduled dose as taken.
    Restricted to patients only (doctors receive 403; unauthorized patients receive 404).
    Derives patient identity strictly from request.user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MedicationDoseSerializer  # hint for drf-spectacular

    def patch(self, request, dose_id):
        if request.user.role != "patient":
            return Response(
                {"detail": "Doctors prescribe medications; only patients record taking doses."},
                status=status.HTTP_403_FORBIDDEN
            )

        patient_profile = getattr(request.user, "patientprofile", None)
        if not patient_profile:
            raise Http404("Dose not found.")

        try:
            dose = MedicationDose.objects.select_related("medication__patient").get(pk=dose_id)
        except MedicationDose.DoesNotExist:
            raise Http404("Dose not found.")

        # Ensure calling patient owns this dose's patient profile
        if dose.medication.patient_id != patient_profile.id:
            raise Http404("Dose not found.")

        dose.status = "taken"
        if not dose.taken_at:
            dose.taken_at = timezone.now()
        dose.save(update_fields=["status", "taken_at"])

        # Also update parent legacy field
        dose.medication.taken_status = True
        dose.medication.save(update_fields=["taken_status"])

        return Response(MedicationDoseSerializer(dose).data, status=status.HTTP_200_OK)


@extend_schema(
    summary="Get Patient Medication Adherence",
    description=(
        "Returns a detailed medication adherence summary for a specific patient. "
        "Accessible to the patient themselves, their assigned doctor, or an admin. "
        "Optional `days` query parameter (default: 7) sets the reporting window. "
        "Returns 404 for unauthorized access to prevent existence enumeration."
    ),
    parameters=[
        OpenApiParameter(
            name="patient_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="PatientProfile.id (primary key of PatientProfile)"
        ),
        OpenApiParameter(
            name="days",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Reporting window in days (default: 7)",
            required=False,
        )
    ],
    responses={
        200: OpenApiResponse(description="Adherence summary with taken/missed/pending counts and percentage"),
        404: OpenApiResponse(description="Patient not found or unauthorized"),
    }
)
class PatientMedicationAdherenceView(APIView):
    """
    Detailed medication adherence summary for a specific patient.
    Accessible to the patient themselves, their assigned doctor, or superusers.
    Uses central get_accessible_patient helper.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, patient_id):
        patient_profile = get_accessible_patient(request.user, patient_id)

        try:
            days = int(request.query_params.get("days", 7))
        except (ValueError, TypeError):
            days = 7

        adherence = calculate_patient_adherence(patient_profile, window_days=days)
        return Response({
            "patient_id": patient_profile.id,
            **adherence
        }, status=status.HTTP_200_OK)