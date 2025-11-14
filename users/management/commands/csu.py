import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Создаёт суперпользователя из переменных "
    "окружения SUPERUSER_EMAIL и SUPERUSER_PASSWORD"

    def handle(self, *args, **options):
        email = os.getenv("SUPERUSER_EMAIL")
        password = os.getenv("SUPERUSER_PASSWORD")
        first_name = os.getenv("SUPERUSER_FIRST_NAME", "")
        last_name = os.getenv("SUPERUSER_LAST_NAME", "")

        if not email or not password:
            raise CommandError(
                "Нужно указать SUPERUSER_EMAIL и SUPERUSER_PASSWORD в .env"
            )

        User = get_user_model()

        if User.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.WARNING(
                    f"ℹ️ Суперпользователь с email '{email}' уже существует"
                )
            )
            return

        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
        self.stdout.write(
            self.style.SUCCESS(f"✅ Суперпользователь создан: {user.email}")
        )
