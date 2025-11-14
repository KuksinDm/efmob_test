from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r"rbac/roles", views.RoleViewSet, basename="role")
router.register(r"rbac/elements", views.BusinessElementViewSet, basename="element")
router.register(r"rbac/access-rules", views.AccessRuleViewSet, basename="access-rule")
router.register(r"items", views.ItemViewSet, basename="item")

urlpatterns = [
    path("auth/register/", views.RegisterView.as_view(), name="auth-register"),
    path("auth/login/", views.LoginView.as_view(), name="auth-login"),
    path("auth/logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("auth/me/", views.MeView.as_view(), name="auth-me"),
    path("auth/refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("", include(router.urls)),
]
