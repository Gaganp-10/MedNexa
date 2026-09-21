from django.http import Http404
from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from accounts.permissions import IsDoctor, IsPatient
from accounts.access import get_accessible_patient
from .models import Medication
from .serializers import MedicationSerializer, MedicationStatusUpdateSerializer


class CreateMedicationView(generics.CreateAPIView):
    """
    Allows a doctor to prescribe medication for their assigned patients.
    Validates assignment using get_accessible_patient.
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

        serializer.save(patient=patient_profile)


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


class MedicationStatusUpdateView(generics.UpdateAPIView):
    """
    Allows a patient to update the taken_status of their own prescribed medication.
    Only the taken_status field is writable.
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
        return Response(MedicationSerializer(medication).data)