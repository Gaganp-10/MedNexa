from django.urls import path
from .views import CreateMedicationView, MedicationListView, MedicationStatusUpdateView

urlpatterns = [
    path("medication/create/", CreateMedicationView.as_view(), name="medication-create"),
    path("medication/<int:patient_id>/", MedicationListView.as_view(), name="medication-list"),
    path("medication/<int:medication_id>/update/", MedicationStatusUpdateView.as_view(), name="medication-status-update"),
]