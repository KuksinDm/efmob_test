import jwt
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import RevokedAccessToken
from .tokens import decode_token


class RequestUserAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth_header = get_authorization_header(request).decode("utf-8")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationFailed("Invalid Authorization header")

        token = parts[1]
        try:
            payload = decode_token(token, expected_type="access")
        except jwt.PyJWTError:
            raise AuthenticationFailed("Invalid or expired token")
        jti = payload.get("jti")
        if jti and RevokedAccessToken.objects.filter(jti=jti).exists():
            raise AuthenticationFailed("Token revoked")

        User = get_user_model()
        try:
            user = User.objects.get(pk=payload.get("sub"), is_active=True)
        except User.DoesNotExist:
            raise AuthenticationFailed("User not found or inactive")

        return (user, token)
