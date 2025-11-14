from datetime import datetime, timezone

import jwt
from django.contrib.auth import get_user_model
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import (
    AccessRoleRule,
    BusinessElement,
    Item,
    RefreshToken,
    RevokedAccessToken,
    Role,
)
from .permissions import HasAccessPermission, IsAdminRole, get_effective_rule
from .schemas import (
    SCHEMA_ACCESS_RULE_VIEWSET,
    SCHEMA_ELEMENT_VIEWSET,
    SCHEMA_ITEM_VIEWSET,
    SCHEMA_LOGIN,
    SCHEMA_LOGOUT_POST,
    SCHEMA_ME_DELETE,
    SCHEMA_ME_GET,
    SCHEMA_ME_PATCH,
    SCHEMA_REFRESH,
    SCHEMA_REGISTER,
    SCHEMA_ROLE_VIEWSET,
)
from .serializers import (
    AccessRoleRuleSerializer,
    BusinessElementSerializer,
    ItemSerializer,
    LoginSerializer,
    MeUpdateSerializer,
    RegisterSerializer,
    RoleSerializer,
    UserOutSerializer,
)
from .tokens import decode_token, generate_access_token, generate_refresh_token

User = get_user_model()


@SCHEMA_REGISTER
class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {"user": UserOutSerializer(user).data}, status=status.HTTP_201_CREATED
        )


@SCHEMA_LOGIN
class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        data = {
            "user": UserOutSerializer(user).data,
            "access": generate_access_token(user.id),
            "refresh": generate_refresh_token(user.id),
        }
        try:
            payload = decode_token(data["refresh"], expected_type="refresh")
            RefreshToken.objects.update_or_create(
                jti=payload.get("jti"),
                defaults={
                    "user": user,
                    "expires_at": datetime.fromtimestamp(
                        payload.get("exp"), tz=timezone.utc
                    ),
                    "revoked": False,
                },
            )
        except jwt.PyJWTError:
            pass
        return Response(data)


@SCHEMA_REFRESH
class RefreshView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        token = request.data.get("refresh")
        if not token:
            return Response({"detail": "refresh token required"}, status=400)
        try:
            payload = decode_token(token, expected_type="refresh")
        except jwt.PyJWTError:
            return Response({"detail": "invalid refresh token"}, status=401)

        jti = payload.get("jti")
        if not jti or RefreshToken.objects.filter(jti=jti, revoked=True).exists():
            return Response({"detail": "invalid refresh token"}, status=401)

        user_id = payload.get("sub")
        try:
            User.objects.get(pk=user_id, is_active=True)
        except User.DoesNotExist:
            return Response({"detail": "user inactive or not found"}, status=401)
        return Response({"access": generate_access_token(user_id)})


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @SCHEMA_ME_GET
    def get(self, request):
        return Response(UserOutSerializer(request.user).data)

    @SCHEMA_ME_PATCH
    def patch(self, request):
        serializer = MeUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserOutSerializer(request.user).data)

    @SCHEMA_ME_DELETE
    def delete(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            access_token = parts[1]
            try:
                access_payload = decode_token(access_token, expected_type="access")
                jti = access_payload.get("jti")
                exp = access_payload.get("exp")
                if jti and exp:
                    RevokedAccessToken.objects.get_or_create(
                        jti=jti,
                        defaults={
                            "user": request.user,
                            "expires_at": datetime.fromtimestamp(exp, tz=timezone.utc),
                        },
                    )
            except jwt.PyJWTError:
                pass

        RefreshToken.objects.filter(user=request.user, revoked=False).update(
            revoked=True
        )

        user = request.user
        user.is_active = False
        user.save(update_fields=["is_active"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @SCHEMA_LOGOUT_POST
    def post(self, request):
        auth = request.META.get("HTTP_AUTHORIZATION", "")
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            access_token = parts[1]
            try:
                access_payload = decode_token(access_token, expected_type="access")
                jti = access_payload.get("jti")
                exp = access_payload.get("exp")
                if jti and exp:
                    RevokedAccessToken.objects.get_or_create(
                        jti=jti,
                        defaults={
                            "user": request.user,
                            "expires_at": datetime.fromtimestamp(exp, tz=timezone.utc),
                        },
                    )
            except jwt.PyJWTError:
                pass

        token = request.data.get("refresh")
        if token:
            try:
                payload = decode_token(token, expected_type="refresh")
                jti = payload.get("jti")
                if jti:
                    RefreshToken.objects.filter(
                        jti=jti, user=request.user, revoked=False
                    ).update(revoked=True)
            except jwt.PyJWTError:
                pass
        else:
            RefreshToken.objects.filter(user=request.user, revoked=False).update(
                revoked=True
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


@SCHEMA_ROLE_VIEWSET
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]
    http_method_names = ["get", "post", "patch", "delete"]


@SCHEMA_ELEMENT_VIEWSET
class BusinessElementViewSet(viewsets.ModelViewSet):
    queryset = BusinessElement.objects.all()
    serializer_class = BusinessElementSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]
    http_method_names = ["get", "post", "patch", "delete"]


@SCHEMA_ACCESS_RULE_VIEWSET
class AccessRuleViewSet(viewsets.ModelViewSet):
    queryset = AccessRoleRule.objects.select_related("role", "element").all()
    serializer_class = AccessRoleRuleSerializer
    permission_classes = [permissions.IsAuthenticated, IsAdminRole]
    http_method_names = ["get", "post", "patch", "delete"]


@SCHEMA_ITEM_VIEWSET
class ItemViewSet(viewsets.ModelViewSet):
    queryset = Item.objects.select_related("owner").all()
    serializer_class = ItemSerializer
    permission_classes = [permissions.IsAuthenticated, HasAccessPermission]
    http_method_names = ["get", "post", "patch", "delete"]
    element_code = "items"

    def get_queryset(self):
        qs = super().get_queryset()
        rule = get_effective_rule(self.request.user, self.element_code)
        if not rule:
            return qs.none()
        if rule.get("read_all"):
            return qs
        if rule.get("read"):
            return qs.filter(owner=self.request.user)
        return qs.none()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
