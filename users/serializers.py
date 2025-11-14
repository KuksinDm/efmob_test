from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from rest_framework import serializers

from .models import AccessRoleRule, BusinessElement, Item, Role

User = get_user_model()


class UserOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "first_name", "middle_name", "last_name", "is_active")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "middle_name",
            "last_name",
            "password",
            "password2",
        )

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise ValidationError({"password2": "Пароли не совпадают"})
        try:
            validate_password(attrs["password"], user=User(email=attrs.get("email")))
        except ValidationError as e:
            raise ValidationError({"password": list(e.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        pwd = validated_data.pop("password")
        user = User(**validated_data)
        user.set_password(pwd)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email, password = attrs["email"], attrs["password"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError({"email": "Неверные учетные данные"})
        if not user.is_active:
            raise ValidationError({"email": "Пользователь деактивирован"})
        if not user.check_password(password):
            raise ValidationError({"password": "Неверные учетные данные"})
        attrs["user"] = user
        return attrs


class MeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("first_name", "middle_name", "last_name")


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ("id", "name")


class BusinessElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessElement
        fields = ("id", "code", "name")


class AccessRoleRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessRoleRule
        fields = (
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


class ItemSerializer(serializers.ModelSerializer):
    owner_email = serializers.ReadOnlyField(source="owner.email")

    class Meta:
        model = Item
        fields = ("id", "title", "owner_email")
