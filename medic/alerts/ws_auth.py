from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_str):
    """
    Validates a raw Simple JWT AccessToken string and retrieves the corresponding User.
    Returns AnonymousUser on any validation failure (invalid, expired, malformed, or missing user).
    Never logs the token.
    """
    try:
        validated_token = AccessToken(token_str)
        user_id = validated_token["user_id"]
        return User.objects.get(id=user_id)
    except Exception:
        return AnonymousUser()


class JWTAuthMiddleware:
    """
    ASGI middleware for Django Channels that extracts and validates a JWT token from
    the WebSocket query string (?token=...).
    
    Rejects unauthenticated, invalid, or expired tokens with close code 4401.
    Strictly avoids logging tokens or raw query strings anywhere.
    """

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "websocket":
            query_string = scope.get("query_string", b"").decode("utf-8", errors="ignore")
            params = parse_qs(query_string)
            token_list = params.get("token")
            raw_token = token_list[0] if token_list else None

            user = await get_user_from_token(raw_token) if raw_token else AnonymousUser()

            if not user or not user.is_authenticated:
                # Reject unauthenticated or invalid token with close code 4401
                message = await receive()
                if message.get("type") == "websocket.connect":
                    await send({"type": "websocket.close", "code": 4401})
                return

            scope["user"] = user

        return await self.inner(scope, receive, send)
