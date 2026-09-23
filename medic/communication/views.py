from django.db import models
from django.db.models import Max
from django.db.models.functions import Coalesce
from django.http import Http404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiTypes

from accounts.access import get_accessible_patient
from accounts.models import PatientProfile
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from .services import dispatch_chat_events


def get_accessible_conversation(user, conversation_id):
    """
    Central access helper for conversations.
    Access is granted if and only if:
    1. The user is a participant (doctor or patient).
    2. The doctor is currently assigned to the patient.

    In all other cases (unassigned doctor, non-participant, nonexistent),
    raises Http404 to avoid leaking existence.
    """
    if not user or not user.is_authenticated:
        raise Http404("Conversation not found.")

    try:
        conv = (
            Conversation.objects
            .select_related("doctor", "patient__user", "patient__doctor")
            .get(id=conversation_id)
        )
    except (Conversation.DoesNotExist, ValueError):
        raise Http404("Conversation not found.")

    is_doctor = (conv.doctor_id == user.id)
    is_patient = (conv.patient.user_id == user.id)

    if not (is_doctor or is_patient):
        raise Http404("Conversation not found.")

    # A doctor may only access conversations with patients currently assigned to them.
    # Accessing a conversation for a patient no longer assigned behaves like it doesn't exist (404).
    if conv.patient.doctor_id != conv.doctor_id:
        raise Http404("Conversation not found.")

    return conv


@extend_schema(
    summary="List Conversations",
    description=(
        "Lists all of the caller's own conversations (as doctor or patient), "
        "paginated, ordered by most recently active first. "
        "Doctors only see conversations with currently assigned patients. "
        "Patients only see their conversation with their currently assigned doctor. "
        "Returns an empty list if no conversations exist."
    ),
    responses={
        200: ConversationSerializer(many=True),
        401: OpenApiResponse(description="Unauthenticated"),
    }
)
class ConversationListView(APIView):
    """
    GET /api/communication/conversations/
    Lists the caller's own conversations (as doctor or patient), paginated,
    most recently active first.

    POST /api/communication/conversations/
    Auto-creates or retrieves conversation on first message send between
    an assigned doctor-patient pair.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == "doctor":
            queryset = Conversation.objects.filter(
                doctor=user,
                patient__doctor=user
            )
        elif user.role == "patient":
            queryset = Conversation.objects.filter(
                patient__user=user,
                doctor=models.F("patient__doctor")
            )
        else:
            queryset = Conversation.objects.none()

        queryset = (
            queryset
            .annotate(latest_active=Coalesce(Max("messages__created_at"), "created_at"))
            .order_by("-latest_active")
            .select_related("doctor", "patient__user")
            .prefetch_related("messages")
        )

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = ConversationSerializer(page, many=True, context={"request": request})
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        summary="Create Conversation or Send First Message",
        description=(
            "Creates or retrieves a conversation between the caller and their assigned counterpart. "
            "If `content` is included in the body, also sends the first message and returns the Message object. "
            "If only `patient_id` is provided (doctor caller), creates the conversation and returns the Conversation object. "
            "Patients do not need to supply any ID — their assigned doctor is resolved server-side."
        ),
        request=OpenApiTypes.OBJECT,
        responses={
            201: MessageSerializer,
            400: OpenApiResponse(description="Missing patient_id or empty content"),
            404: OpenApiResponse(description="Assigned doctor/patient not found"),
        }
    )
    def post(self, request):
        user = request.user
        patient = None

        if user.role == "doctor":
            patient_id = request.data.get("patient_id")
            if not patient_id:
                raise ValidationError({"patient_id": ["patient_id is required for doctors to initiate a conversation."]})
            patient = get_accessible_patient(user, patient_id)
            if patient.doctor_id != user.id:
                raise Http404("Patient not found.")
            doctor = user
        elif user.role == "patient":
            patient = getattr(user, "patientprofile", None)
            if not patient or not patient.doctor:
                raise Http404("No assigned doctor found.")
            doctor = patient.doctor
        else:
            raise PermissionDenied("Only doctors and patients can access conversations.")

        conversation, _ = Conversation.objects.get_or_create(doctor=doctor, patient=patient)

        # If initial content is provided, create the first message
        content = request.data.get("content")
        if content is not None:
            stripped = content.strip() if isinstance(content, str) else ""
            if not stripped:
                raise ValidationError({"content": ["Message content cannot be empty or whitespace only."]})
            if len(stripped) > 4000:
                raise ValidationError({"content": ["Message content cannot exceed 4000 characters."]})

            message = Message.objects.create(
                conversation=conversation,
                sender=user,
                content=stripped
            )
            conversation.save(update_fields=["updated_at"])
            dispatch_chat_events(message)
            return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)

        return Response(
            ConversationSerializer(conversation, context={"request": request}).data,
            status=status.HTTP_201_CREATED
        )


@extend_schema(
    methods=["GET"],
    summary="List Conversation Messages",
    description=(
        "Returns paginated message history for a specific conversation, "
        "ordered **oldest-to-newest** (ascending created_at — standard chronological chat order). "
        "A conversation with zero messages returns an empty results list (HTTP 200), not an error. "
        "Verifies that the caller is a current participant and that the doctor is still assigned."
    ),
    parameters=[
        OpenApiParameter(
            name="pk",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Conversation.id (primary key)"
        )
    ],
    responses={
        200: MessageSerializer(many=True),
        404: OpenApiResponse(description="Conversation not found or caller is not an active participant"),
    }
)
@extend_schema(
    methods=["POST"],
    summary="Send Message",
    description=(
        "Sends a message to the specified conversation. "
        "**Sender is always `request.user` — any `sender` or `sender_id` field in the body is ignored.** "
        "Validates that content is non-empty, non-whitespace, and ≤4000 characters. "
        "\n\n**Auto-creation on first message**: if `<pk>` is a `PatientProfile.id` "
        "(i.e., the conversation doesn't exist yet), the conversation is automatically created "
        "before sending the message. This is the recommended way to start a conversation — "
        "no separate 'create conversation' step is needed. "
        "Once a conversation exists, subsequent POSTs should use the `Conversation.id` returned "
        "in the conversations list.\n\n"
        "After persisting the message, it is broadcast to the `chat_<conversation_id>` WebSocket group "
        "and a lightweight notification is dispatched to the recipient's personal channel."
    ),
    parameters=[
        OpenApiParameter(
            name="pk",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description=(
                "**First message**: pass PatientProfile.id (doctor caller) — conversation is auto-created. "
                "**Subsequent messages**: pass Conversation.id from the conversations list."
            )
        )
    ],
    request=MessageSerializer,
    responses={
        201: MessageSerializer,
        400: OpenApiResponse(description="Empty or whitespace-only message content"),
        404: OpenApiResponse(description="Conversation/patient not found or caller not an active participant"),
    }
)
class ConversationMessagesView(APIView):
    """
    GET /api/communication/conversations/<id>/messages/
    Paginated message history for that conversation, ordered oldest-to-newest (chronological).

    POST /api/communication/conversations/<id>/messages/
    Send a message. Sender is always request.user.
    Supports auto-creating the conversation on first message send if <id> is a patient_id
    or if the conversation record has not been initialized yet.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        conversation = get_accessible_conversation(request.user, pk)
        # Oldest-to-newest (chronological ordering)
        messages_qs = conversation.messages.select_related("sender").order_by("created_at")

        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(messages_qs, request, view=self)
        serializer = MessageSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, pk):
        conversation = None
        # 1. Try resolving pk as Conversation.id
        try:
            conversation = get_accessible_conversation(request.user, pk)
        except Http404:
            # 2. Support auto-creation on first message send if pk is patient_id
            if request.user.role == "doctor":
                try:
                    patient = get_accessible_patient(request.user, pk)
                    if patient.doctor_id == request.user.id:
                        conversation, _ = Conversation.objects.get_or_create(
                            doctor=request.user,
                            patient=patient
                        )
                except Http404:
                    pass
            elif request.user.role == "patient":
                patient = getattr(request.user, "patientprofile", None)
                if patient and patient.doctor and (pk == patient.id or pk == patient.doctor_id or pk == 0):
                    conversation, _ = Conversation.objects.get_or_create(
                        doctor=patient.doctor,
                        patient=patient
                    )

        if not conversation:
            raise Http404("Conversation not found.")

        # Re-verify assignment
        if conversation.patient.doctor_id != conversation.doctor_id:
            raise Http404("Conversation not found.")

        # Validate content: non-empty, non-whitespace, max 4000 characters
        raw_content = request.data.get("content")
        if raw_content is None or not isinstance(raw_content, str) or not raw_content.strip():
            raise ValidationError({"content": ["Message content cannot be empty or whitespace only."]})

        stripped = raw_content.strip()
        if len(stripped) > 4000:
            raise ValidationError({"content": ["Message content cannot exceed 4000 characters."]})

        # Sender is always request.user — never trust sender from request body
        message = Message.objects.create(
            conversation=conversation,
            sender=request.user,
            content=stripped
        )
        conversation.save(update_fields=["updated_at"])

        # Broadcast to conversation WebSocket group and push notification to recipient
        dispatch_chat_events(message)

        return Response(MessageSerializer(message).data, status=status.HTTP_201_CREATED)


@extend_schema(
    summary="Mark Message as Read",
    description=(
        "Marks a specific message as read (`is_read = true`). "
        "**Only the recipient (not the sender) may mark a message read.** "
        "If the sender attempts to mark their own message read, 403 Forbidden is returned. "
        "If the caller is not a participant, 404 is returned to prevent existence enumeration. "
        "If the doctor is no longer assigned to the patient, 404 is returned."
    ),
    parameters=[
        OpenApiParameter(
            name="pk",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.PATH,
            description="Message primary key"
        )
    ],
    responses={
        200: MessageSerializer,
        403: OpenApiResponse(description="Sender cannot mark their own message as read"),
        404: OpenApiResponse(description="Message not found or caller is not an active participant"),
    }
)
class MessageReadReceiptView(APIView):
    """
    PATCH /api/communication/messages/<id>/read/
    Marks a single message as read.
    Only the recipient (not the sender) can mark it read.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer  # hint for drf-spectacular

    def patch(self, request, pk):
        try:
            message = (
                Message.objects
                .select_related("conversation__patient__doctor", "conversation__doctor", "conversation__patient__user")
                .get(id=pk)
            )
        except (Message.DoesNotExist, ValueError):
            raise Http404("Message not found.")

        conv = message.conversation
        # Check active assignment
        if conv.patient.doctor_id != conv.doctor_id:
            raise Http404("Message not found.")

        # Must be participant
        is_doctor = (conv.doctor_id == request.user.id)
        is_patient = (conv.patient.user_id == request.user.id)
        if not (is_doctor or is_patient):
            raise Http404("Message not found.")

        # Recipient rule: only recipient (NOT sender) can mark as read
        if message.sender_id == request.user.id:
            raise PermissionDenied("Sender cannot mark their own message as read.")

        message.is_read = True
        message.save(update_fields=["is_read"])
        return Response(MessageSerializer(message).data, status=status.HTTP_200_OK)
