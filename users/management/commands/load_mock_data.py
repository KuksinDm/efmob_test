import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from users.models import AccessRoleRule, BusinessElement, Item, Role


def to_bool(v: str) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "on", "y"}


def load_csv(path: Path, required_cols: list[str]) -> list[dict]:
    if not path.exists():
        raise CommandError(f"CSV файл не найден: {path}")
    rows: list[dict] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise CommandError(f"{path.name}: пустой или без заголовка")
        missing = [c for c in required_cols if c not in reader.fieldnames]
        if missing:
            raise CommandError(f"{path.name}: отсутствуют колонки: {missing}")
        for i, row in enumerate(reader, start=2):
            rows.append({
                k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()
            })
    return rows


class Command(BaseCommand):
    help = "Загружает мок-данные из CSV: роли, элементы, правила, демо-пользователи, "
    " демо-items. Пароли можно сбросить с --reset-passwords"

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            default="users/management/data",
            help="Каталог с CSV файлами (по умолчанию users/management/data)",
        )
        parser.add_argument(
            "--reset-passwords",
            action="store_true",
            help="Принудительно сбрасывать пароли демо-пользователей из CSV",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        data_dir = Path(options["data_dir"])
        reset_passwords = options["reset_passwords"]
        User = get_user_model()

        roles_by_name = self._load_roles(data_dir)
        elements_by_code = self._load_elements(data_dir)
        self._load_access_rules(data_dir, roles_by_name, elements_by_code)
        users_by_email = self._load_demo_users(
            data_dir, User, roles_by_name, reset_passwords
        )
        self._load_demo_items(data_dir, User, users_by_email)

        self.stdout.write(self.style.SUCCESS("✅ Загрузка мок-данных завершена"))

    def _load_roles(self, data_dir: Path) -> dict[str, Role]:
        roles_csv = load_csv(data_dir / "roles.csv", ["name"])
        roles_by_name: dict[str, Role] = {}
        for row in roles_csv:
            name = row["name"]
            role, _ = Role.objects.get_or_create(name=name)
            roles_by_name[name] = role
        self.stdout.write(self.style.SUCCESS(f"✔ Ролей: {len(roles_by_name)}"))
        return roles_by_name

    def _load_elements(self, data_dir: Path) -> dict[str, BusinessElement]:
        elements_csv = load_csv(data_dir / "business_elements.csv", ["code", "name"])
        elements_by_code: dict[str, BusinessElement] = {}
        for row in elements_csv:
            code, name = row["code"], row["name"]
            el, created = BusinessElement.objects.get_or_create(
                code=code, defaults={"name": name}
            )
            if not created and el.name != name:
                el.name = name
                el.save(update_fields=["name"])
            elements_by_code[code] = el
        self.stdout.write(self.style.SUCCESS(f"✔ Элементов: {len(elements_by_code)}"))
        return elements_by_code

    def _load_access_rules(
        self,
        data_dir: Path,
        roles_by_name: dict[str, Role],
        elements_by_code: dict[str, BusinessElement],
    ) -> None:
        rules_csv = load_csv(
            data_dir / "access_role_rules.csv",
            [
                "role",
                "element",
                "read",
                "read_all",
                "create",
                "update",
                "update_all",
                "delete",
                "delete_all",
            ],
        )
        for row in rules_csv:
            r_name = row["role"]
            e_code = row["element"]
            if r_name not in roles_by_name:
                raise CommandError(f"Правило для неизвестной роли: {r_name}")
            if e_code not in elements_by_code:
                raise CommandError(f"Правило для неизвестного элемента: {e_code}")
            AccessRoleRule.objects.update_or_create(
                role=roles_by_name[r_name],
                element=elements_by_code[e_code],
                defaults={
                    "read": to_bool(row["read"]),
                    "read_all": to_bool(row["read_all"]),
                    "create": to_bool(row["create"]),
                    "update": to_bool(row["update"]),
                    "update_all": to_bool(row["update_all"]),
                    "delete": to_bool(row["delete"]),
                    "delete_all": to_bool(row["delete_all"]),
                },
            )
        self.stdout.write(self.style.SUCCESS("✔ Правила доступа созданы/обновлены"))

    def _load_demo_users(
        self,
        data_dir: Path,
        User,
        roles_by_name: dict[str, Role],
        reset_passwords: bool,
    ) -> dict[str, any]:
        users_csv = load_csv(
            data_dir / "demo_users.csv",
            ["email", "first_name", "last_name", "roles"],
        )
        users_by_email: dict[str, any] = {}
        for row in users_csv:
            email = row["email"]
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": row["first_name"],
                    "last_name": row["last_name"],
                    "is_active": True,
                },
            )
            if created or reset_passwords:
                pwd = row.get("password") or "Passw0rd!"
                user.set_password(pwd)
                user.save(update_fields=["password"] if not created else None)

            role_names = [r.strip() for r in row["roles"].split(",") if r.strip()]
            unknown = [r for r in role_names if r not in roles_by_name]
            if unknown:
                raise CommandError(
                    f"Для пользователя {email} не найдены роли: {unknown}"
                )
            user.roles.set([roles_by_name[r] for r in role_names])
            users_by_email[email] = user
        self.stdout.write(
            self.style.SUCCESS(f"✔ Демо-пользователей: {len(users_by_email)}")
        )
        return users_by_email

    def _load_demo_items(
        self, data_dir: Path, User, users_by_email: dict[str, any]
    ) -> None:
        items_csv = load_csv(data_dir / "demo_items.csv", ["title", "owner_email"])
        for row in items_csv:
            owner_email = row["owner_email"]
            owner = (
                users_by_email.get(owner_email)
                or User.objects.filter(email=owner_email).first()
            )
            if owner is None:
                raise CommandError(f"Не найден владелец для item: {owner_email}")
            Item.objects.get_or_create(title=row["title"], owner=owner)
        self.stdout.write(self.style.SUCCESS(f"✔ Демо-items: {len(items_csv)}"))
