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

> Для быстрого старта есть команда `python manage.py load_mock_data`, которая читает CSV из `users/management/data/` (роли, элементы, правила, пользователи, demo-items). Её можно повторно запускать для синхронизации справочников или подменять каталог данных.

## RBAC-правила
- `read` — доступ только к собственным объектам.
- `read_all` — чтение любых объектов элемента.
- Аналогично для `create`, `update`, `update_all`, `delete`, `delete_all`.
- Permission `HasAccessPermission` автоматически применяет правила, проверяет owner, возвращает 401/403.
- Элемент указывается в `viewset.element_code` (например, `"items"`), и permission берёт агрегированное правило по ролям пользователя.

### Агрегация правил
- Эффективное правило вычисляется как логическое OR по всем ролям пользователя для данного элемента.
- Если для элемента нет ни одного правила, все флаги считаются `False`.

### Матрица методов → прав
| Метод | Проверяемый флаг | Область действия |
| --- | --- | --- |
| GET (list/retrieve) | `read` или `read_all` | `read_all` — ко всем записям; `read` — только свои |
| POST | `create` | Создание записи от имени пользователя (становится владельцем) |
| PUT/PATCH | `update` или `update_all` | `update_all` — ко всем; `update` — только свои |
| DELETE | `delete` или `delete_all` | `delete_all` — ко всем; `delete` — только свои |

## JWT-аутентификация (коротко)
- Логин (`POST /api/auth/login/`) выдаёт `access` и `refresh`. `refresh` фиксируется в БД (с `jti`).
- Аутентификация — заголовок `Authorization: Bearer <access>`; валидируется и проверяется в blacklist.
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
python manage.py csu          # создаёт суперпользователя из переменных
python manage.py load_mock_data  # заполняет роли/элементы/демо-данные из CSV
python manage.py runserver
```

### Запуск с Postgres
- В `.env` установите `USE_POSTGRES=True` и заполните `POSTGRES_*` переменные.
- Убедитесь, что БД существует и доступна пользователю.
- Затем выполните миграции и инициализацию как в разделе выше (`csu`, `load_mock_data`), после чего запустите сервер.

### Docker (план)
- Собрать образ с зависимостями (`pip install -e .`).
- В entrypoint добавить шаги: `python manage.py migrate && python manage.py start` (команда `start` уже объединяет `csu + load_mock_data`; при желании можно расширить её другими импортами).
- После инициализации запускать WSGI/ASGI-сервер (например, `gunicorn config.wsgi:application`).
> Когда docker-compose будет добавлен, достаточно пробросить `.env` и окружение Postgres — вся подготовка данных выполнится автоматически через `manage.py start`.

## Менеджмент-команды
- `python manage.py csu` — создаёт суперпользователя из `SUPERUSER_*`.
- `python manage.py load_mock_data [--data-dir=… --reset-passwords]` — читает CSV и создаёт роли, элементы, правила, демо-пользователей, demo-Items.
- `python manage.py start` — агрегирует `csu` + `load_mock_data` (можно расширить доп. импортами).

## Проверка сценариев
1. `POST /api/auth/register/` — создаёт пользователя.
2. `POST /api/auth/login/` — получаем access/refresh.
3. CRUD над `/api/items/`:
   - без токена → 401,
   - с ролью без прав → 403,
   - с правами `read` → видим только свои элементы,
   - с правами `read_all`/`update_all`/`delete_all` → доступ ко всем.
4. `POST /api/auth/logout/` → access попадает в blacklist, refresh отзывается.
5. `POST /api/auth/refresh/` c отозванным refresh → 401.
6. `DELETE /api/auth/me/` → `is_active=False`, любые токены становятся недействительными.

## Дальнейшие улучшения
- Добавить автотесты (auth, RBAC, отзыв токенов).
- Подготовить Docker/compose (когда появится Dockerfile).