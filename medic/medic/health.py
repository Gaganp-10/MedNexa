from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiResponse


@extend_schema(
    summary="System Health Check",
    description="Public health check endpoint. Returns current service status. No authentication required.",
    responses={
        200: OpenApiResponse(description='{"status": "running", "service": "medic backend", "version": "1.0"}')
    }
)
class SystemHealthView(APIView):
    """
    Public system health check endpoint.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({
            "status": "running",
            "service": "medic backend",
            "version": "1.0"
        })