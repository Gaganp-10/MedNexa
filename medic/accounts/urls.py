from django.urls import path
from .views import (
    DoctorOverviewView,
    DoctorPatientsView,
    PatientHealthLogsView,
    PatientWoundImagesView,
    PatientAlertsView,
    PatientRecoveryTrendView,
    PatientRiskPredictionView,
    AuthMeView,
    PatientProfileMeView,
)

urlpatterns = [
    path("auth/me/", AuthMeView.as_view(), name="auth-me"),
    path("patient/profile/", PatientProfileMeView.as_view(), name="patient-profile-me"),
    path("doctor/overview/", DoctorOverviewView.as_view(), name="doctor-overview"),
    path("doctor/patients/", DoctorPatientsView.as_view(), name="doctor-patients"),
    path("patient/<int:patient_id>/logs/", PatientHealthLogsView.as_view(), name="patient-logs"),
    path("patient/<int:patient_id>/wounds/", PatientWoundImagesView.as_view(), name="patient-wounds"),
    path("patient/<int:patient_id>/alerts/", PatientAlertsView.as_view(), name="patient-alerts"),
    path("patient/<int:patient_id>/recovery-trend/", PatientRecoveryTrendView.as_view(), name="patient-recovery-trend"),
    path("patient/<int:patient_id>/risk/", PatientRiskPredictionView.as_view(), name="patient-risk"),
]