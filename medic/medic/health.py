from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny


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