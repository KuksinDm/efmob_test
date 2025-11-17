from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Запускает все необходимые команды для инициализации проекта"

    def handle(self, *args, **options):
        self.stdout.write("🚀 Начинаем инициализацию проекта...")

        self.stdout.write("\n👤 Создание суперпользователя...")
        call_command("csu")

        self.stdout.write("\n📥 Инициализация RBAC...")
        call_command("load_mock_data")

        self.stdout.write(self.style.SUCCESS("\n✨ Все команды успешно выполнены!"))
