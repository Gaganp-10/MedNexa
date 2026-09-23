from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes

from .models import Alert
from .serializers import AlertReadUpdateSerializer
from accounts.access import get_accessible_patient


@extend_schema(
    summary="Mark Alert as Read (Doctor)",
    description=(
        "Marks a system alert as read. "
        "Only the currently assigned doctor of the alert's patient may update an alert. "
        "Superusers may also update. Patients cannot mark alerts read. "
        "Returns 404 (not 403) for any unauthorized caller to prevent existence enumeration."
    ),
    parameters=[
        OpenApiParameter(
            name="alert_id",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Alert primary key"
        )
    ],
    request=AlertReadUpdateSerializer,
    responses={
        200: AlertReadUpdateSerializer,
        404: OpenApiResponse(description="Alert not found or caller is not the assigned doctor"),
    }
)
class AlertMarkReadView(APIView):
    """
    Allows only the assigned doctor of an alert's patient to mark the alert as read.
    Uses central get_accessible_patient helper. Only is_read is writable.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, alert_id):
        try:
            alert = Alert.objects.select_related("patient__user", "patient__doctor").get(pk=alert_id)
        except Alert.DoesNotExist:
            raise Http404("Alert not found.")

        # Ensure patient is accessible
        patient = get_accessible_patient(request.user, alert.patient_id)

        # Enforce that only the assigned doctor (or superuser) can update alert read status
        if not request.user.is_superuser and (request.user.role != "doctor" or patient.doctor_id != request.user.id):
            raise Http404("Alert not found.")

        serializer = AlertReadUpdateSerializer(alert, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
