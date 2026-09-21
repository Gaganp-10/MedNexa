from rest_framework.permissions import BasePermission


class IsDoctor(BasePermission):
    """
    Allows access only to authenticated users with the 'doctor' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, "role", None) == "doctor"
        )


class IsPatient(BasePermission):
    """
    Allows access only to authenticated users with the 'patient' role.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, "role", None) == "patient"
        )