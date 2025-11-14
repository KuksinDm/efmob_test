from drf_spectacular.utils import (
    OpenApiTypes,
    extend_schema,
    extend_schema_view,
    inline_serializer,
)
from rest_framework import serializers

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

LoginResponse = inline_serializer(
    name="LoginResponse",
    fields={
        "user": UserOutSerializer(),
        "access": serializers.CharField(),
        "refresh": serializers.CharField(),
    },
)

RefreshResponse = inline_serializer(
    name="RefreshResponse",
    fields={"access": serializers.CharField()},
)

LogoutRequest = inline_serializer(
    name="LogoutRequest",
    fields={"refresh": serializers.CharField(required=False)},
)

SCHEMA_REGISTER = extend_schema(
    tags=["Auth"],
    request=RegisterSerializer,
    summary="Регистрация",
    description="Создаёт нового пользователя. Возвращает профиль пользователя.",
    responses={201: UserOutSerializer},
    auth=[],
)
SCHEMA_LOGIN = extend_schema(
    tags=["Auth"],
    request=LoginSerializer,
    summary="Логин",
    description="Аутентификация по email и паролю. Возвращает пару "
        "токенов (access/refresh) и профиль. Если refresh-токен просрочен, "
        "некорректен или отозван (блеклист) — 401.",
    responses={200: LoginResponse},
    auth=[],
)
SCHEMA_REFRESH = extend_schema(
    tags=["Auth"],
    request=inline_serializer(
        name="RefreshRequest", fields={"refresh": serializers.CharField()}
    ),
    summary="Обновление access-токена",
    description=(
        "Принимает refresh-токен и возвращает новый access-токен. "
        "Если токен просрочен, некорректен или отозван (блеклист) — 401."
    ),
    responses={200: RefreshResponse},
    auth=[],
)
SCHEMA_ME_GET = extend_schema(
    tags=["Users"],
    summary="Профиль текущего пользователя",
    description="Возвращает профиль авторизованного пользователя.",
    responses={200: UserOutSerializer},
)
SCHEMA_ME_PATCH = extend_schema(
    tags=["Users"],
    summary="Обновление профиля",
    description="Изменяет имя/фамилию/отчество текущего пользователя.",
    request=MeUpdateSerializer,
    responses={200: UserOutSerializer},
)
SCHEMA_ME_DELETE = extend_schema(
    tags=["Users"],
    summary="Мягкое удаление аккаунта",
    description="Ставит is_active=False, отозвает все активные refresh-токены "
        "и access-токены и разлогинивает пользователя. Возвращает 204 без тела.",
    responses={204: OpenApiTypes.NONE},
)
SCHEMA_LOGOUT_POST = extend_schema(
    tags=["Auth"],
    summary="Выход из системы",
    description=(
        "При вызове текущий access отзывается. Если передан refresh — он будет отозван;"
        " если не передан — будут отозваны все активные refresh пользователя."
        "Возвращает 204."
    ),
    request=LogoutRequest,
    responses={204: OpenApiTypes.NONE},
)

# RBAC: роли
SCHEMA_ROLE_VIEWSET = extend_schema_view(
    list=extend_schema(
        tags=["RBAC"],
        summary="Список ролей",
        responses={200: RoleSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["RBAC"], summary="Роль", responses={200: RoleSerializer}
    ),
    create=extend_schema(
        tags=["RBAC"],
        summary="Создать роль",
        request=RoleSerializer,
        responses={201: RoleSerializer},
    ),
    partial_update=extend_schema(
        tags=["RBAC"],
        summary="Частичное обновление роли",
        request=RoleSerializer,
        responses={200: RoleSerializer},
    ),
    destroy=extend_schema(
        tags=["RBAC"], summary="Удалить роль", responses={204: OpenApiTypes.NONE}
    ),
)

# RBAC: элементы
SCHEMA_ELEMENT_VIEWSET = extend_schema_view(
    list=extend_schema(
        tags=["RBAC"],
        summary="Список элементов",
        responses={200: BusinessElementSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["RBAC"], summary="Элемент", responses={200: BusinessElementSerializer}
    ),
    create=extend_schema(
        tags=["RBAC"],
        summary="Создать элемент",
        request=BusinessElementSerializer,
        responses={201: BusinessElementSerializer},
    ),
    partial_update=extend_schema(
        tags=["RBAC"],
        summary="Частичное обновление элемента",
        request=BusinessElementSerializer,
        responses={200: BusinessElementSerializer},
    ),
    destroy=extend_schema(
        tags=["RBAC"], summary="Удалить элемент", responses={204: OpenApiTypes.NONE}
    ),
)

# RBAC: правила доступа роль × элемент
SCHEMA_ACCESS_RULE_VIEWSET = extend_schema_view(
    list=extend_schema(
        tags=["RBAC"],
        summary="Список правил доступа",
        responses={200: AccessRoleRuleSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["RBAC"],
        summary="Правило доступа",
        responses={200: AccessRoleRuleSerializer},
    ),
    create=extend_schema(
        tags=["RBAC"],
        summary="Создать правило доступа",
        request=AccessRoleRuleSerializer,
        responses={201: AccessRoleRuleSerializer},
    ),
    partial_update=extend_schema(
        tags=["RBAC"],
        summary="Частичное обновление правила",
        request=AccessRoleRuleSerializer,
        responses={200: AccessRoleRuleSerializer},
    ),
    destroy=extend_schema(
        tags=["RBAC"],
        summary="Удалить правило доступа",
        responses={204: OpenApiTypes.NONE},
    ),
)

# Items
SCHEMA_ITEM_VIEWSET = extend_schema_view(
    list=extend_schema(
        tags=["Items"],
        summary="Список айтемов",
        description="Возвращает все или только свои — согласно флагам read/read_all.",
        responses={200: ItemSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Items"], summary="Детали айтема", responses={200: ItemSerializer}
    ),
    create=extend_schema(
        tags=["Items"],
        summary="Создать айтем",
        request=ItemSerializer,
        responses={201: ItemSerializer},
    ),
    partial_update=extend_schema(
        tags=["Items"],
        summary="Частичное обновление айтема",
        request=ItemSerializer,
        responses={200: ItemSerializer},
    ),
    destroy=extend_schema(
        tags=["Items"], summary="Удалить айтем", responses={204: OpenApiTypes.NONE}
    ),
)
