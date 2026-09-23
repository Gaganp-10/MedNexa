from django.urls import path
from .views import (
    ConversationListView,
    ConversationMessagesView,
    MessageReadReceiptView,
)

urlpatterns = [
    path('communication/conversations/', ConversationListView.as_view(), name='conversation-list'),
    path('communication/conversations/<int:pk>/messages/', ConversationMessagesView.as_view(), name='conversation-messages'),
    path('communication/messages/<int:pk>/read/', MessageReadReceiptView.as_view(), name='message-mark-read'),
]
