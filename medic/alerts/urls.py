from django.urls import path
from .views import AlertMarkReadView

urlpatterns = [
    path("alerts/<int:alert_id>/read/", AlertMarkReadView.as_view(), name="alert-mark-read"),
]
