from django.urls import path
from .views import (
    CreateHealthLogView,
    HealthLogListView,
    UploadWoundImageView,
    WoundImageListView,
    WoundImageFileStreamView,
)

urlpatterns = [
    path('health/create/', CreateHealthLogView.as_view(), name='health-log-create'),
    path('health/logs/', HealthLogListView.as_view(), name='health-log-list'),
    path('wound/upload/', UploadWoundImageView.as_view(), name='wound-upload'),
    path('wound/images/', WoundImageListView.as_view(), name='wound-image-list'),
    path('wound/images/<int:image_id>/file/', WoundImageFileStreamView.as_view(), name='wound-image-file'),
]