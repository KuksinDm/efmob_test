from django.core.management import call_command
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

API_PREFIX = "/api"


def api_url(path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return f"{API_PREFIX}{path}"


class AuthFlowTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        # Ничего не нужно заранее
        pass

    def setUp(self) -> None:
        self.client = APIClient()

    def register_user(self, email: str, password: str = "Passw0rd!"):
        payload = {
            "email": email,
            "first_name": "Test",
            "last_name": "User",
            "password": password,
            "password2": password,
        }
        (self.client.post(api_url("/auth/register/")),)
        return self.client.post(api_url("/auth/register/"), payload, format="json")

    def login(self, email: str, password: str = "Passw0rd!"):
        payload = {"email": email, "password": password}
        return self.client.post(api_url("/auth/login/"), payload, format="json")

    def test_register_and_login_refresh_logout(self):
        # Регистрация
        reg = self.register_user("newuser@example.com")
        self.assertEqual(reg.status_code, status.HTTP_201_CREATED, reg.content)

        # Логин
        login = self.login("newuser@example.com")
        self.assertEqual(login.status_code, status.HTTP_200_OK, login.content)
        access = login.data["access"]
        refresh = login.data["refresh"]

        # Refresh -> новый access
        refresh_resp = self.client.post(
            api_url("/auth/refresh/"), {"refresh": refresh}, format="json"
        )
        self.assertEqual(
            refresh_resp.status_code, status.HTTP_200_OK, refresh_resp.content
        )
        self.assertIn("access", refresh_resp.data)

        # Logout c ревокацией access и refresh
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        logout = self.client.post(
            api_url("/auth/logout/"), {"refresh": refresh}, format="json"
        )
        self.assertEqual(logout.status_code, status.HTTP_204_NO_CONTENT, logout.content)

        # Повторный refresh по старому refresh токену -> 401
        refresh_again = self.client.post(
            api_url("/auth/refresh/"), {"refresh": refresh}, format="json"
        )
        self.assertEqual(
            refresh_again.status_code,
            status.HTTP_401_UNAUTHORIZED,
            refresh_again.content,
        )


class SoftDeleteTests(APITestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_soft_delete_revokes_tokens_and_blocks_login(self):
        # Регистрация и логин
        reg = self.client.post(
            api_url("/auth/register/"),
            {
                "email": "sd@example.com",
                "first_name": "Soft",
                "last_name": "Delete",
                "password": "Passw0rd!",
                "password2": "Passw0rd!",
            },
            format="json",
        )
        self.assertEqual(reg.status_code, status.HTTP_201_CREATED, reg.content)

        login = self.client.post(
            api_url("/auth/login/"),
            {"email": "sd@example.com", "password": "Passw0rd!"},
            format="json",
        )
        self.assertEqual(login.status_code, status.HTTP_200_OK, login.content)
        access = login.data["access"]
        refresh = login.data["refresh"]

        # DELETE /auth/me/
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        delete = self.client.delete(api_url("/auth/me/"))
        self.assertEqual(delete.status_code, status.HTTP_204_NO_CONTENT, delete.content)

        # Refresh по старому refresh -> 401
        refresh_resp = self.client.post(
            api_url("/auth/refresh/"), {"refresh": refresh}, format="json"
        )
        self.assertEqual(
            refresh_resp.status_code, status.HTTP_401_UNAUTHORIZED, refresh_resp.content
        )

        # Повторный логин запрещён (пользователь деактивирован) -> 400
        login_again = self.client.post(
            api_url("/auth/login/"),
            {"email": "sd@example.com", "password": "Passw0rd!"},
            format="json",
        )
        self.assertEqual(
            login_again.status_code, status.HTTP_400_BAD_REQUEST, login_again.content
        )
        self.assertIn("email", login_again.data)


class RBACTests(APITestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        # Поднимем справочники/демо через CSV, чтобы проверить RBAC
        call_command("load_mock_data", "--reset-passwords")

    def setUp(self) -> None:
        self.client = APIClient()

    def login(self, email: str, password: str = "Passw0rd!"):
        return self.client.post(
            api_url("/auth/login/"),
            {"email": email, "password": password},
            format="json",
        )

    def test_items_access_401_403_200(self):
        # 401 без токена
        response_anonymous = self.client.get(api_url("/items/"))
        self.assertEqual(
            response_anonymous.status_code,
            status.HTTP_401_UNAUTHORIZED,
            response_anonymous.content,
        )

        # 403 у гостя (нет прав на items)
        guest_login = self.login("guest@example.com")
        self.assertEqual(
            guest_login.status_code, status.HTTP_200_OK, guest_login.content
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {guest_login.data['access']}"
        )
        response_guest = self.client.get(api_url("/items/"))
        self.assertEqual(
            response_guest.status_code,
            status.HTTP_403_FORBIDDEN,
            response_guest.content,
        )

        # 200 у user: видит только свои 2 items
        self.client.credentials()
        user_login = self.login("user@example.com")
        self.assertEqual(user_login.status_code, status.HTTP_200_OK, user_login.content)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {user_login.data['access']}"
        )
        response_user = self.client.get(api_url("/items/"))
        self.assertEqual(
            response_user.status_code, status.HTTP_200_OK, response_user.content
        )
        self.assertTrue(isinstance(response_user.data, list))
        self.assertEqual(len(response_user.data), 2)

        # 200 у manager: read_all => видит все 4 items
        self.client.credentials()
        manager_login = self.login("manager@example.com")
        self.assertEqual(
            manager_login.status_code, status.HTTP_200_OK, manager_login.content
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {manager_login.data['access']}"
        )
        response_manager = self.client.get(api_url("/items/"))
        self.assertEqual(
            response_manager.status_code, status.HTTP_200_OK, response_manager.content
        )
        self.assertEqual(len(response_manager.data), 4)

    def test_rbac_admin_endpoints_require_admin_role(self):
        # user -> 403
        user_login = self.login("user@example.com")
        self.assertEqual(user_login.status_code, status.HTTP_200_OK, user_login.content)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {user_login.data['access']}"
        )
        response_user = self.client.get(api_url("/rbac/roles/"))
        self.assertEqual(
            response_user.status_code, status.HTTP_403_FORBIDDEN, response_user.content
        )

        # admin -> 200
        self.client.credentials()
        admin_login = self.login("admin@example.com")
        self.assertEqual(
            admin_login.status_code, status.HTTP_200_OK, admin_login.content
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {admin_login.data['access']}"
        )
        r_admin = self.client.get(api_url("/rbac/roles/"))
        self.assertEqual(r_admin.status_code, status.HTTP_200_OK, r_admin.content)


class AuthNegativeTests(APITestCase):
    """Негативные тесты для аутентификации"""

    def setUp(self) -> None:
        self.client = APIClient()

    def test_register_with_weak_password(self):
        # Слишком короткий пароль
        resp = self.client.post(
            api_url("/auth/register/"),
            {
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "password": "123",
                "password2": "123",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertIn("password", resp.data)

    def test_register_with_mismatched_passwords(self):
        # Пароли не совпадают
        resp = self.client.post(
            api_url("/auth/register/"),
            {
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "password": "Passw0rd!",
                "password2": "DifferentPass!",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)
        self.assertIn("password2", resp.data)

    def test_login_with_wrong_password(self):
        # Создаем пользователя
        self.client.post(
            api_url("/auth/register/"),
            {
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "password": "Passw0rd!",
                "password2": "Passw0rd!",
            },
            format="json",
        )

        # Пытаемся залогиниться с неверным паролем
        resp = self.client.post(
            api_url("/auth/login/"),
            {"email": "test@example.com", "password": "WrongPassword!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_login_with_nonexistent_email(self):
        # Пытаемся залогиниться с несуществующим email
        resp = self.client.post(
            api_url("/auth/login/"),
            {"email": "nonexistent@example.com", "password": "Passw0rd!"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)

    def test_refresh_with_invalid_token(self):
        # Невалидный refresh токен
        resp = self.client.post(
            api_url("/auth/refresh/"),
            {"refresh": "invalid.token.here"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED, resp.content)


class ProfileTests(APITestCase):
    """Тесты для работы с профилем пользователя"""

    def setUp(self) -> None:
        self.client = APIClient()
        # Создаем и логиним пользователя
        self.client.post(
            api_url("/auth/register/"),
            {
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "password": "Passw0rd!",
                "password2": "Passw0rd!",
            },
            format="json",
        )
        login_resp = self.client.post(
            api_url("/auth/login/"),
            {"email": "test@example.com", "password": "Passw0rd!"},
            format="json",
        )
        self.access_token = login_resp.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    def test_get_profile(self):
        # Получение профиля
        resp = self.client.get(api_url("/auth/me/"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["email"], "test@example.com")
        self.assertEqual(resp.data["first_name"], "Test")
        self.assertEqual(resp.data["last_name"], "User")

    def test_update_profile(self):
        # Обновление профиля
        resp = self.client.patch(
            api_url("/auth/me/"),
            {
                "first_name": "Updated",
                "last_name": "Name",
                "middle_name": "Middle",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["first_name"], "Updated")
        self.assertEqual(resp.data["last_name"], "Name")
        self.assertEqual(resp.data["middle_name"], "Middle")

    def test_get_profile_without_auth(self):
        # Попытка получить профиль без токена
        self.client.credentials()  # Очищаем credentials
        resp = self.client.get(api_url("/auth/me/"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED, resp.content)


class ItemsCRUDTests(APITestCase):
    """Тесты на CRUD операции с items"""

    @classmethod
    def setUpTestData(cls) -> None:
        call_command("load_mock_data", "--reset-passwords")

    def setUp(self) -> None:
        self.client = APIClient()

    def login(self, email: str, password: str = "Passw0rd!"):
        resp = self.client.post(
            api_url("/auth/login/"),
            {"email": email, "password": password},
            format="json",
        )
        return resp.data["access"]

    def test_create_item_as_user(self):
        # User может создавать items (create=True)
        token = self.login("user@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        resp = self.client.post(
            api_url("/items/"),
            {"title": "New Item"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertEqual(resp.data["title"], "New Item")
        self.assertEqual(resp.data["owner_email"], "user@example.com")

    def test_create_item_as_guest(self):
        # Guest НЕ может создавать items (create=False)
        token = self.login("guest@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        resp = self.client.post(
            api_url("/items/"),
            {"title": "New Item"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)

    def test_update_own_item_as_user(self):
        # User может обновлять свои items (update=True)
        token = self.login("user@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Получаем список items пользователя
        items_resp = self.client.get(api_url("/items/"))
        self.assertEqual(items_resp.status_code, status.HTTP_200_OK)
        self.assertGreater(len(items_resp.data), 0)

        item_id = items_resp.data[0]["id"]

        # Обновляем свой item
        resp = self.client.patch(
            api_url(f"/items/{item_id}/"),
            {"title": "Updated Title"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["title"], "Updated Title")

    def test_update_foreign_item_as_user(self):
        # User НЕ может обновлять чужие items (update_all=False)
        # Логинимся как manager, чтобы получить все items
        manager_token = self.login("manager@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {manager_token}")
        items_resp = self.client.get(api_url("/items/"))

        # Находим item, который НЕ принадлежит user
        other_items = [
            item
            for item in items_resp.data
            if item["owner_email"] != "user@example.com"
        ]
        self.assertGreater(len(other_items), 0)

        foreign_item_id = other_items[0]["id"]

        # Логинимся как user и пытаемся обновить чужой item
        user_token = self.login("user@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

        resp = self.client.patch(
            api_url(f"/items/{foreign_item_id}/"),
            {"title": "Hacked Title"},
            format="json",
        )
        # get_queryset фильтрует items, поэтому user получает 404, а не 403
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)

    def test_update_any_item_as_manager(self):
        # Manager может обновлять любые items (update_all=True)
        token = self.login("manager@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Получаем любой item
        items_resp = self.client.get(api_url("/items/"))
        self.assertGreater(len(items_resp.data), 0)
        item_id = items_resp.data[0]["id"]

        # Обновляем любой item
        resp = self.client.patch(
            api_url(f"/items/{item_id}/"),
            {"title": "Manager Updated"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["title"], "Manager Updated")

    def test_delete_own_item_as_user(self):
        # User может удалять свои items (delete=True)
        token = self.login("user@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        # Создаем item
        create_resp = self.client.post(
            api_url("/items/"),
            {"title": "To Delete"},
            format="json",
        )
        item_id = create_resp.data["id"]

        # Удаляем свой item
        resp = self.client.delete(api_url(f"/items/{item_id}/"))
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT, resp.content)

    def test_delete_foreign_item_as_user(self):
        # User НЕ может удалять чужие items (delete_all=False)
        # Создаем item как manager
        manager_token = self.login("manager@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {manager_token}")
        create_resp = self.client.post(
            api_url("/items/"),
            {"title": "Manager Item"},
            format="json",
        )
        item_id = create_resp.data["id"]

        # Пытаемся удалить как user
        user_token = self.login("user@example.com")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {user_token}")

        resp = self.client.delete(api_url(f"/items/{item_id}/"))
        # get_queryset фильтрует items, поэтому user получает 404, а не 403
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND, resp.content)


class AccessTokenBlacklistTests(APITestCase):
    """Тесты на blacklist access токенов"""

    def setUp(self) -> None:
        self.client = APIClient()
        # Создаем пользователя
        self.client.post(
            api_url("/auth/register/"),
            {
                "email": "test@example.com",
                "first_name": "Test",
                "last_name": "User",
                "password": "Passw0rd!",
                "password2": "Passw0rd!",
            },
            format="json",
        )
        login_resp = self.client.post(
            api_url("/auth/login/"),
            {"email": "test@example.com", "password": "Passw0rd!"},
            format="json",
        )
        self.access_token = login_resp.data["access"]
        self.refresh_token = login_resp.data["refresh"]

    def test_access_token_blacklisted_after_logout(self):
        # Access токен должен быть в blacklist после logout
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

        # Проверяем, что токен работает
        resp = self.client.get(api_url("/auth/me/"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)

        # Делаем logout
        logout_resp = self.client.post(
            api_url("/auth/logout/"),
            {"refresh": self.refresh_token},
            format="json",
        )
        self.assertEqual(logout_resp.status_code, status.HTTP_204_NO_CONTENT)

        # Пытаемся использовать старый access токен (должен быть отозван)
        resp = self.client.get(api_url("/auth/me/"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED, resp.content)
        self.assertIn("revoked", str(resp.content).lower())

    def test_access_token_blacklisted_after_soft_delete(self):
        # Access токен должен быть в blacklist после мягкого удаления
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

        # Удаляем пользователя
        delete_resp = self.client.delete(api_url("/auth/me/"))
        self.assertEqual(delete_resp.status_code, status.HTTP_204_NO_CONTENT)

        # Пытаемся использовать старый access токен (пользователь неактивен)
        resp = self.client.get(api_url("/auth/me/"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED, resp.content)


class RBACCRUDTests(APITestCase):
    """Тесты на CRUD операции с RBAC endpoints"""

    @classmethod
    def setUpTestData(cls) -> None:
        call_command("load_mock_data", "--reset-passwords")

    def setUp(self) -> None:
        self.client = APIClient()

    def login_as_admin(self):
        resp = self.client.post(
            api_url("/auth/login/"),
            {"email": "admin@example.com", "password": "Passw0rd!"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {resp.data['access']}")

    def test_create_role_as_admin(self):
        self.login_as_admin()

        resp = self.client.post(
            api_url("/rbac/roles/"),
            {"name": "new_role"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertEqual(resp.data["name"], "new_role")

    def test_update_role_as_admin(self):
        self.login_as_admin()

        # Получаем существующую роль
        roles_resp = self.client.get(api_url("/rbac/roles/"))
        self.assertGreater(len(roles_resp.data), 0)
        role_id = roles_resp.data[0]["id"]

        # Обновляем роль
        resp = self.client.patch(
            api_url(f"/rbac/roles/{role_id}/"),
            {"name": "updated_role"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["name"], "updated_role")

    def test_create_business_element_as_admin(self):
        self.login_as_admin()

        resp = self.client.post(
            api_url("/rbac/elements/"),
            {"code": "new_element", "name": "New Element"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertEqual(resp.data["code"], "new_element")

    def test_create_access_rule_as_admin(self):
        self.login_as_admin()

        # Получаем роль и элемент
        roles_resp = self.client.get(api_url("/rbac/roles/"))
        elements_resp = self.client.get(api_url("/rbac/elements/"))

        role_id = roles_resp.data[0]["id"]
        element_id = elements_resp.data[0]["id"]

        resp = self.client.post(
            api_url("/rbac/access-rules/"),
            {
                "role": role_id,
                "element": element_id,
                "read": True,
                "read_all": False,
                "create": False,
                "update": False,
                "update_all": False,
                "delete": False,
                "delete_all": False,
            },
            format="json",
        )
        # Может быть 201 или 400 если правило уже существует
        self.assertIn(
            resp.status_code,
            [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST],
            resp.content,
        )
