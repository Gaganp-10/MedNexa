from django.http import Http404
from .models import PatientProfile


def get_accessible_patient(user, patient_id):
    """
    Central access helper for patient-scoped resources.
    
    patient_id always refers to PatientProfile.id (primary key).
    
    Access is granted if:
    1. The user is a superuser.
    2. The user is the patient themselves (patient_profile.user == user).
    3. The user is the assigned doctor (patient_profile.doctor == user).
    
    In all other cases (unauthenticated, unassigned doctor, other patient,
    or nonexistent patient), raises Http404 to avoid leaking patient existence.
    """
    if not user or not user.is_authenticated:
        raise Http404("Patient not found.")

    try:
        patient_profile = PatientProfile.objects.select_related("user", "doctor").get(pk=patient_id)
    except PatientProfile.DoesNotExist:
        raise Http404("Patient not found.")

    if user.is_superuser:
        return patient_profile

    if patient_profile.user_id == user.id:
        return patient_profile

    if patient_profile.doctor_id == user.id:
        return patient_profile

    # Raise Http404 to avoid disclosing whether a patient record exists
    raise Http404("Patient not found.")
