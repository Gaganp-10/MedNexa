from django.urls import path
from .views import (
    CreateMedicationView,
    MedicationListView,
    MedicationStatusUpdateView,
    PatientTodayDosesView,
    PatientUpcomingDosesView,
    TakeDoseView,
    PatientMedicationAdherenceView,
)

urlpatterns = [
    path("medication/create/", CreateMedicationView.as_view(), name="medication-create"),
    path("medication/<int:patient_id>/", MedicationListView.as_view(), name="medication-list"),
    path("medication/<int:medication_id>/update/", MedicationStatusUpdateView.as_view(), name="medication-status-update"),
    path("medication/doses/today/", PatientTodayDosesView.as_view(), name="medication-doses-today"),
    path("medication/doses/upcoming/", PatientUpcomingDosesView.as_view(), name="medication-doses-upcoming"),
    path("medication/doses/<int:dose_id>/take/", TakeDoseView.as_view(), name="medication-dose-take"),
    path("patient/<int:patient_id>/medication-adherence/", PatientMedicationAdherenceView.as_view(), name="patient-medication-adherence"),
]