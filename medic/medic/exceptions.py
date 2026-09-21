import logging
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404
from django.core.exceptions import PermissionDenied

logger = logging.getLogger("medic.security")


def custom_exception_handler(exc, context):
    """
    Consistent JSON error response handler.
    Ensures consistent error formatting and prevents internal stack traces or sensitive data from leaking.
    """
    # Call DRF's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    view_name = context.get("view").__class__.__name__ if context.get("view") else "UnknownView"
    request = context.get("request")
    user_str = f"User {request.user.id} ({getattr(request.user, 'role', 'unknown')})" if request and request.user.is_authenticated else "AnonymousUser"

    if response is not None:
        if response.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN):
            logger.warning(
                f"Authorization failure: status={response.status_code}, view={view_name}, user={user_str}, path={request.path if request else 'unknown'}"
            )
        
        # Standardize structure if it's not already standard
        if not isinstance(response.data, dict) or "error" not in response.data:
            response.data = {
                "error": True,
                "detail": response.data,
                "status_code": response.status_code
            }
        return response

    # If DRF returned None, it's an unhandled exception (e.g. 500)
    logger.error(
        f"Unhandled server error in {view_name} for {user_str}: {exc.__class__.__name__}: {str(exc)}",
        exc_info=True
    )

    return Response(
        {
            "error": True,
            "detail": "An internal error occurred. Please contact system support.",
            "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR
    )
