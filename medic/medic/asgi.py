"""
ASGI config for medic project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'medic.settings')

django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from alerts.consumers import AlertConsumer, PatientNotificationConsumer
from communication.consumers import ChatConsumer
from alerts.ws_auth import JWTAuthMiddleware

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter([
            path("ws/alerts/", AlertConsumer.as_asgi()),
            path("ws/notifications/", PatientNotificationConsumer.as_asgi()),
            path("ws/chat/<int:conversation_id>/", ChatConsumer.as_asgi()),
        ])
    ),
})