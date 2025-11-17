# Собственная система аутентификации и авторизации

Тестовое задание: бэкенд на Django/DRF + Postgres с собственной реализацией JWT-аутентификации, отзывом токенов и RBAC-правами на основе ролей и бизнес-элементов.

## Стек
- Python 3.12
- Django 5 / DRF 3
- django-environ, django-filter
- drf-spectacular (Swagger/Redoc)
- PyJWT + кастомная authentication (DRF `BaseAuthentication`)
- Postgres (по умолчанию SQLite для локального запуска)

## Возможности
- Регистрация / логин / logout / refresh токена.
- Кастомный `User` с UUID, email-логином и ролями (bcrypt-хеширование).
- JWT access/refresh: хранение refresh в БД, отзыв access через blacklist, мягкое удаление пользователя.
- RBAC-модель: `roles`, `business_elements`, `access_role_rules` с флагами `read/read_all/create/update/update_all/delete/delete_all`.
- Mock-ресурс `items` для демонстрации 401/403 и сценариев owner vs all.
- Админские CRUD-эндпоинты для управления ролями, элементами и правилами.
- Swagger-документация и management-команды для инициализации суперпользователя.

## Схема данных
| Модель | Назначение |
| --- | --- |
| `users_user` | Кастомный пользователь (UUID, email, ФИО, M2M роли) |
| `users_role` | Названия ролей (admin, manager, user, …) |
| `users_businesselement` | Список бизнес-объектов (users, items, rbac, …) |
| `users_accessrolerule` | Права роли на элемент (по флагам `*_permission`) |
| `users_item` | Демонстрационный ресурс с owner |
| `users_refreshtoken` | Refresh-токены с `revoked`, `expires_at`, `jti` |
| `users_revokedaccesstoken` | Blacklist access-токенов (по `jti`) |

> Для быстрого старта есть команда `python manage.py load_mock_data`, которая читает CSV из `users/management/data/` (роли, элементы, правила, пользователи, demo-items). Ее можно повторно запускать для синхронизации справочников или подменять каталог данных.

## RBAC-правила
- `read` - доступ только к собственным объектам.
- `read_all` - чтение любых объектов элемента.
- Аналогично для `create`, `update`, `update_all`, `delete`, `delete_all`.
- Permission `HasAccessPermission` автоматически применяет правила, проверяет owner, возвращает 401/403.
- Элемент указывается в `viewset.element_code` (например, `"items"`), и permission берет агрегированное правило по ролям пользователя.

### Агрегация правил
- Эффективное правило вычисляется как логическое OR по всем ролям пользователя для данного элемента.
- Если для элемента нет ни одного правила, все флаги считаются `False`.

### Матрица методов → прав
| Метод | Проверяемый флаг | Область действия |
| --- | --- | --- |
| GET (list/retrieve) | `read` или `read_all` | `read_all` - ко всем записям; `read` - только свои |
| POST | `create` | Создание записи от имени пользователя (становится владельцем) |
| PUT/PATCH | `update` или `update_all` | `update_all` - ко всем; `update` - только свои |
| DELETE | `delete` или `delete_all` | `delete_all` - ко всем; `delete` - только свои |

## JWT-аутентификация (коротко)
- Логин (`POST /api/auth/login/`) выдает `access` и `refresh`. `refresh` фиксируется в БД (с `jti`).
- Аутентификация - заголовок `Authorization: Bearer <access>`; валидируется и проверяется в blacklist.
- Обновление (`POST /api/auth/refresh/`) возвращает новый `access` при валидном неотозванном `refresh`.
- Logout (`POST /api/auth/logout/`) добавляет текущий `access` в blacklist и отзывает `refresh`(ы).
- Soft delete (`DELETE /api/auth/me/`) помечает пользователя `is_active=False` и отзывает все токены.

## API

### Аутентификация (`/api/auth/*`)
| Метод | Путь | Описание |
| --- | --- | --- |
| `POST` | `/auth/register/` | Создать пользователя (ФИО + email + пароль). Возвращает профиль. |
| `POST` | `/auth/login/` | Получить пару токенов и профиль. |
| `POST` | `/auth/refresh/` | Обновить access-токен по refresh (401 при отзыве/истечении). |
| `GET/PATCH/DELETE` | `/auth/me/` | Профиль, обновление ФИО, мягкое удаление (ставит `is_active=False` и отзывает токены). |
| `POST` | `/auth/logout/` | Отозвать текущий access и все refresh (или конкретный refresh, если передан в теле). |

### RBAC и бизнес-объекты (`/api/*`)
| Метод | Путь | Описание |
| --- | --- | --- |
| CRUD | `/rbac/roles/` | Управление ролями (только роль `admin`). |
| CRUD | `/rbac/elements/` | Управление бизнес-элементами (только роль `admin`). |
| CRUD | `/rbac/access-rules/` | Настройка прав (только роль `admin`). |
| CRUD | `/items/` | Демонстрационное API, защищено `HasAccessPermission`. |

Swagger/Redoc доступны на `/api/docs` и `/api/redoc`.

## Переменные окружения
Создайте `.env` рядом с `manage.py`. Основные ключи:
```
SECRET_KEY=
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

USE_POSTGRES=False
POSTGRES_DB=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_HOST=
POSTGRES_PORT=5432

JWT_ALGORITHM=HS256
JWT_ACCESS_TTL_MIN=30
JWT_REFRESH_TTL_DAYS=7

SUPERUSER_EMAIL=
SUPERUSER_PASSWORD=
SUPERUSER_FIRST_NAME=
SUPERUSER_LAST_NAME=
```

## Запуск
```bash
python -m venv .venv
.venv\Scripts\activate  # или source .venv/bin/activate
pip install -e .
python manage.py migrate
cp .env.example .env  # при необходимости заполнить
python manage.py csu          # создает суперпользователя из переменных
python manage.py load_mock_data  # заполняет роли/элементы/демо-данные из CSV
python manage.py runserver
```

### Запуск с Postgres
- В `.env` установите `USE_POSTGRES=True` и заполните `POSTGRES_*` переменные.
- Убедитесь, что БД существует и доступна пользователю.
- Затем выполните миграции и инициализацию как в разделе выше (`csu`, `load_mock_data`), после чего запустите сервер.

### Запуск через Docker / Docker Compose
Требуется Docker и Docker Compose.

1) Подготовьте переменные окружения
- Возьмите `.env.example` и создайте `.env` в корне проекта (`efmob_test/`).
- Обязательно укажите настройки БД и включите Postgres:
  - `USE_POSTGRES=True`
  - `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
  - `POSTGRES_HOST=db_efmob_test` (имя сервиса в compose), `POSTGRES_PORT=5432`

2) Запуск с помощью Docker Compose
```bash
docker compose up --build
```
- Compose поднимет `db` (Postgres) и `web` (Django).
- `entrypoint.sh` внутри контейнера выполнит миграции и `python manage.py start`
  (создаст суперпользователя из `.env` и загрузит мок‑данные из CSV).

3) Проверка
- Приложение: http://localhost:8000/
- Swagger: http://localhost:8000/api/docs
- Redoc: http://localhost:8000/api/redoc

4) Полезные команды
```bash
# остановить контейнеры
docker compose down

# пересобрать и запустить заново
docker compose up --build

# полностью очистить том с данными Postgres
docker compose down -v
```

## Менеджмент-команды
- `python manage.py csu` - создает суперпользователя из `SUPERUSER_*`.
- `python manage.py load_mock_data [--data-dir=… --reset-passwords]` - читает CSV и создает роли, элементы, правила, демо-пользователей, demo-Items.
- `python manage.py start` - агрегирует `csu` + `load_mock_data` (можно расширить доп. импортами).

## Проверка сценариев
1. `POST /api/auth/register/` - создает пользователя.
2. `POST /api/auth/login/` - получаем access/refresh.
3. CRUD над `/api/items/`:
   - без токена → 401,
   - с ролью без прав → 403,
   - с правами `read` → видим только свои элементы,
   - с правами `read_all`/`update_all`/`delete_all` → доступ ко всем.
4. `POST /api/auth/logout/` → access попадает в blacklist, refresh отзывается.
5. `POST /api/auth/refresh/` c отозванным refresh → 401.
6. `DELETE /api/auth/me/` → `is_active=False`, любые токены становятся недействительными.

## Тестирование

Проект покрыт автотестами (25 тестов, ~75% покрытие функционала).

### Запуск тестов

# Запуск всех тестов
python manage.py test

# Запуск с подробным выводом
python manage.py test --verbosity=2

# Запуск конкретного тестового класса
python manage.py test users.tests.ItemsCRUDTests

# Запуск конкретного теста
python manage.py test users.tests.ItemsCRUDTests.test_create_item_as_user### Покрытие тестами

**1. AuthFlowTests** - Основной flow аутентификации:
- ✅ Регистрация → Логин → Refresh → Logout
- ✅ Проверка отзыва refresh токенов

**2. AuthNegativeTests** - Негативные сценарии (5 тестов):
- ✅ Регистрация со слабым паролем
- ✅ Регистрация с несовпадающими паролями
- ✅ Логин с неверным паролем
- ✅ Логин с несуществующим email
- ✅ Refresh с невалидным токеном

**3. ProfileTests** - Работа с профилем (3 теста):
- ✅ Получение профиля (GET /auth/me/)
- ✅ Обновление профиля (PATCH /auth/me/)
- ✅ Проверка 401 без токена

**4. SoftDeleteTests** - Мягкое удаление:
- ✅ Деактивация пользователя
- ✅ Отзыв всех токенов
- ✅ Блокировка повторного логина

**5. ItemsCRUDTests** - CRUD операции с items (8 тестов):
- ✅ Создание items (разрешено user, запрещено guest)
- ✅ Обновление своих items (user)
- ✅ Попытка обновления чужих items (403/404)
- ✅ Обновление любых items (manager с update_all)
- ✅ Удаление своих/чужих items
- ✅ Проверка прав owner vs _all

**6. AccessTokenBlacklistTests** - Blacklist токенов (2 теста):
- ✅ Access токен в blacklist после logout
- ✅ Access токен в blacklist после мягкого удаления

**7. RBACTests** - Система разграничения доступа (2 теста):
- ✅ Проверка 401/403 для items
- ✅ Разделение прав read/read_all
- ✅ Доступ к RBAC endpoints только для admin

**8. RBACCRUDTests** - CRUD для RBAC (4 теста):
- ✅ Создание/обновление ролей (admin)
- ✅ Создание бизнес-элементов (admin)
- ✅ Создание правил доступа (admin)

### Особенности реализации

- Все тесты используют in-memory SQLite для скорости
- Демо-данные загружаются через `load_mock_data` для RBAC-тестов
- Тесты проверяют правильные HTTP-коды (401 vs 403)
- Проверяется работа blacklist для access токенов
- Тестируется логика owner vs _all permissions

## Дальнейшие улучшения
- Добавить тесты на истекшие токены
- Добавить тесты на множественные роли у пользователя
- Тесты на edge cases (несуществующие элементы, некорректные правила)
- Integration тесты с реальной БД Postgres
