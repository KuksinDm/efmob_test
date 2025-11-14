from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from .models import (
    AccessRoleRule,
    BusinessElement,
    Item,
    RefreshToken,
    RevokedAccessToken,
    Role,
    User,
)


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name", "middle_name")


class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "middle_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "roles",
            "groups",
            "user_permissions",
        )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = ("id", "email", "first_name", "last_name", "is_active", "is_staff")
    list_filter = ("is_active", "is_staff", "is_superuser", "roles")
    ordering = ("id",)
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "middle_name")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "roles",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "middle_name",
                    "is_staff",
                    "is_superuser",
                    "is_active",
                    "roles",
                ),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    ordering = ("id",)


@admin.register(BusinessElement)
class BusinessElementAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name")
    search_fields = ("code", "name")
    ordering = ("id",)


@admin.register(AccessRoleRule)
class AccessRoleRuleAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "role",
        "element",
        "read",
        "read_all",
        "create",
        "update",
        "update_all",
        "delete",
        "delete_all",
    )
    list_filter = ("role", "element")
    search_fields = ("role__name", "element__code")
    ordering = ("id",)
    raw_id_fields = ("role", "element")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner")
    search_fields = ("title", "owner__email")
    list_filter = ("owner",)
    ordering = ("id",)


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ("jti", "user", "revoked", "expires_at", "created_at")
    search_fields = ("jti", "user__email")
    list_filter = ("revoked",)


@admin.register(RevokedAccessToken)
class RevokedAccessTokenAdmin(admin.ModelAdmin):
    list_display = ("jti", "user", "expires_at", "created_at")
    search_fields = ("jti", "user__email")
