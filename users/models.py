import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class Role(models.Model):
    name = models.CharField(
        max_length=64,
        unique=True,
        verbose_name="Название роли",
        help_text="Уникальное название роли пользователя в системе",
    )

    class Meta:
        verbose_name = "Роль"
        verbose_name_plural = "Роли"

    def __str__(self):
        return self.name


class BusinessElement(models.Model):
    code = models.SlugField(
        max_length=64,
        unique=True,
        verbose_name="Код элемента",
        help_text="Уникальный код бизнес-элемента (slug)",
    )
    name = models.CharField(
        max_length=128,
        verbose_name="Название элемента",
        help_text="Название бизнес-элемента",
    )

    class Meta:
        verbose_name = "Бизнес-элемент"
        verbose_name_plural = "Бизнес-элементы"

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name="ID пользователя",
        help_text="Уникальный идентификатор пользователя в формате UUID",
    )
    username = None
    email = models.EmailField(
        unique=True,
        verbose_name="Email",
        help_text="Email пользователя для входа в систему",
    )

    middle_name = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Отчество",
        help_text="Отчество пользователя (необязательно)",
    )

    roles = models.ManyToManyField(
        Role,
        blank=True,
        verbose_name="Роли",
        help_text="Роли пользователя для управления доступом",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self) -> str:
        return self.email


class AccessRoleRule(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        verbose_name="Роль",
        help_text="Роль, для которой устанавливаются права доступа",
    )
    element = models.ForeignKey(
        BusinessElement,
        on_delete=models.CASCADE,
        verbose_name="Бизнес-элемент",
        help_text="Бизнес-элемент, к которому применяются права доступа",
    )
    read = models.BooleanField(
        default=False,
        verbose_name="Чтение",
        help_text="Право на чтение собственных элементов",
    )
    read_all = models.BooleanField(
        default=False,
        verbose_name="Чтение всех",
        help_text="Право на чтение всех элементов",
    )
    create = models.BooleanField(
        default=False,
        verbose_name="Создание",
        help_text="Право на создание элементов",
    )
    update = models.BooleanField(
        default=False,
        verbose_name="Обновление",
        help_text="Право на обновление собственных элементов",
    )
    update_all = models.BooleanField(
        default=False,
        verbose_name="Обновление всех",
        help_text="Право на обновление всех элементов",
    )
    delete = models.BooleanField(
        default=False,
        verbose_name="Удаление",
        help_text="Право на удаление собственных элементов",
    )
    delete_all = models.BooleanField(
        default=False,
        verbose_name="Удаление всех",
        help_text="Право на удаление всех элементов",
    )

    class Meta:
        unique_together = ("role", "element")
        verbose_name = "Правило доступа роли"
        verbose_name_plural = "Правила доступа ролей"


class RefreshToken(models.Model):
    jti = models.CharField(
        max_length=36,
        unique=True,
        verbose_name="JWT ID",
        help_text="Уникальный идентификатор JWT токена (JTI)",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
        verbose_name="Пользователь",
        help_text="Пользователь, которому принадлежит токен",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
        help_text="Дата и время создания токена",
    )
    expires_at = models.DateTimeField(
        verbose_name="Дата истечения",
        help_text="Дата и время истечения срока действия токена",
    )
    revoked = models.BooleanField(
        default=False,
        verbose_name="Отозван",
        help_text="Флаг, указывающий, был ли токен отозван",
    )
    replaced_by = models.CharField(
        max_length=36,
        null=True,
        blank=True,
        verbose_name="Заменен на",
        help_text="JTI токена, который заменил данный токен при обновлении",
    )

    class Meta:
        verbose_name = "Refresh токен"
        verbose_name_plural = "Refresh токены"

    def __str__(self):
        return f"{self.jti} ({'revoked' if self.revoked else 'active'})"


class RevokedAccessToken(models.Model):
    jti = models.CharField(
        max_length=36,
        unique=True,
        verbose_name="JWT ID",
        help_text="Уникальный идентификатор JWT токена (JTI)",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="revoked_access_tokens",
        verbose_name="Пользователь",
        help_text="Пользователь, которому принадлежал токен",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Дата создания",
        help_text="Дата и время создания записи об отозванном токене",
    )
    expires_at = models.DateTimeField(
        verbose_name="Дата истечения",
        help_text="Дата и время истечения срока действия токена",
    )

    class Meta:
        verbose_name = "Отозванный access токен"
        verbose_name_plural = "Отозванные access токены"

    def __str__(self):
        return f"{self.jti} (expires {self.expires_at})"


# ----------Items----------
"""
По хорошему для этого должно быть отдельное приложение,
но для тестового задания я это делать не стал.
"""


class Item(models.Model):
    title = models.CharField(
        max_length=200,
        verbose_name="Название",
        help_text="Название элемента",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Владелец",
        help_text="Пользователь, которому принадлежит элемент",
    )

    class Meta:
        verbose_name = "Элемент"
        verbose_name_plural = "Элементы"

    def __str__(self):
        return self.title
