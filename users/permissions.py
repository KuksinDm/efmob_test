from typing import Optional

from django.contrib.auth import get_user_model
from rest_framework.exceptions import NotAuthenticated
from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import AccessRoleRule, BusinessElement

User = get_user_model()


def get_effective_rule(user, element_code: str) -> Optional[dict]:
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        element = BusinessElement.objects.get(code=element_code)
    except BusinessElement.DoesNotExist:
        return None
    roles = user.roles.all()
    rules = AccessRoleRule.objects.filter(role__in=roles, element=element)
    if not rules.exists():
        return {
            "read": False,
            "read_all": False,
            "create": False,
            "update": False,
            "update_all": False,
            "delete": False,
            "delete_all": False,
        }
    agg = {
        "read": False,
        "read_all": False,
        "create": False,
        "update": False,
        "update_all": False,
        "delete": False,
        "delete_all": False,
    }
    for rule in rules:
        agg["read"] = agg["read"] or rule.read
        agg["read_all"] = agg["read_all"] or rule.read_all
        agg["create"] = agg["create"] or rule.create
        agg["update"] = agg["update"] or rule.update
        agg["update_all"] = agg["update_all"] or rule.update_all
        agg["delete"] = agg["delete"] or rule.delete
        agg["delete_all"] = agg["delete_all"] or rule.delete_all
    return agg


class HasAccessPermission(BasePermission):
    message = "Forbidden"

    def has_permission(self, request, view):
        element_code = getattr(view, "element_code", None)
        if not element_code:
            return True

        rule = get_effective_rule(request.user, element_code)
        if rule is None:
            raise NotAuthenticated()

        method = request.method.upper()
        if method in SAFE_METHODS:
            return rule["read"] or rule["read_all"]
        if method == "POST":
            return rule["create"]
        if method in ("PUT", "PATCH"):
            return rule["update"] or rule["update_all"]
        if method == "DELETE":
            return rule["delete"] or rule["delete_all"]
        return False

    def has_object_permission(self, request, view, obj):
        element_code = getattr(view, "element_code", None)
        if not element_code:
            return True
        rule = get_effective_rule(request.user, element_code)
        if rule is None:
            raise NotAuthenticated()

        method = request.method.upper()
        if method in SAFE_METHODS:
            if rule["read_all"]:
                return True
            return getattr(obj, "owner_id", None) == getattr(
                request.user, "id", None
            ) or (
                element_code == "users"
                and getattr(obj, "id", None) == getattr(request.user, "id", None)
            )
        if method in ("PUT", "PATCH"):
            if rule["update_all"]:
                return True
            return getattr(obj, "owner_id", None) == getattr(
                request.user, "id", None
            ) or (
                element_code == "users"
                and getattr(obj, "id", None) == getattr(request.user, "id", None)
            )
        if method == "DELETE":
            if rule["delete_all"]:
                return True
            return getattr(obj, "owner_id", None) == getattr(
                request.user, "id", None
            ) or (
                element_code == "users"
                and getattr(obj, "id", None) == getattr(request.user, "id", None)
            )
        if method == "POST":
            return rule["create"]
        return False


class IsAdminRole(BasePermission):
    message = "Admin role required"

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and user.roles.filter(name="admin").exists()
        )
